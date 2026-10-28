"""Real instruction models recover dispatch across copies and unrelated work."""

import hashlib
import struct
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from extractor.native_runtime import preload_libstdcxx

preload_libstdcxx()

import angr

from extractor.binary_cfg import build_static_cfg
from extractor.binary_inventory import PinnedBinary
from extractor.dispatch_discovery import recover_block_dispatch
from extractor.fresh import extract_fresh_function


BASE = 0x400000
TABLE = BASE + 0x100
FIRST = BASE + 0x40
SECOND = BASE + 0x50


def fixture(*, copied=False, clobbered=False, bounded=True, byte_index=False,
            terminal_call=False):
    # lea rdi, table; movzx eax, byte [rsi]; [and eax, 1];
    # [mov rdx, rdi]; xor ecx, ecx; [xor edi, edi]; jmp [base+rax*8]
    code = b"\x48\x8d\x3d" + struct.pack("<i", TABLE - (BASE + 7))
    code += b"\x0f\xb6\x06" if bounded else b"\x48\x89\xf0"
    if bounded and not byte_index:
        code += b"\x83\xe0\x01"
    if copied:
        code += b"\x48\x89\xfa"
    code += b"\x31\xc9"
    if clobbered:
        code += b"\x31\xff"
    code += b"\xff\x24\xc2" if copied else b"\xff\x24\xc7"
    if terminal_call:
        code = b"\xe8" + struct.pack("<i", FIRST - (BASE + 5))
    raw = bytearray(b"\x90" * (0x900 if byte_index else 0x110))
    raw[:len(code)] = code
    raw[0x40:0x46] = b"\xb8\x11\0\0\0\xc3"
    raw[0x50:0x56] = b"\xb8\x22\0\0\0\xc3"
    raw[0x100:0x110] = struct.pack("<QQ", FIRST, SECOND)
    if byte_index:
        raw[0x100:0x900] = struct.pack("<QQ", FIRST, SECOND) * 128
    return bytes(raw), code


class DispatchDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)

    def pinned(self, *, interior_target=None, earlier_block=False, **options):
        raw, code = fixture(**options)
        if interior_target is not None:
            modified = bytearray(raw)
            struct.pack_into("<Q", modified, 0x100, interior_target)
            if earlier_block:
                # A known direct edge makes the first LEA a separate block,
                # while the dispatch still recomputes its base locally.
                prefix = b"\x90\xeb\x0d" + b"\x90" * 13
                relocated = bytearray(code)
                struct.pack_into("<i", relocated, 3, TABLE - (BASE + 16 + 7))
                modified[:16 + len(code)] = prefix + relocated
            raw = bytes(modified)
        path = Path(self.temporary.name) / "dispatch.bin"
        path.write_bytes(raw)
        project = angr.load_shellcode(raw, arch="amd64", load_address=BASE)
        manifest = {
            "roots": {"interpreter": {"address": BASE,
                                        "size": len(code) if options.get("terminal_call") else 0x60,
                                        "symbol": "interpreter"}},
            "primitive_boundaries": {}, "call_graph": {"interpreter": {}},
            "image_sha256": hashlib.sha256(raw).hexdigest(), "open_transfers": True,
        }
        instructions = [{"address": item.address} for item in
                        project.arch.capstone.disasm(code, BASE)]
        return PinnedBinary(path, manifest, project), instructions

    def test_symbol_free_dispatch_with_intervening_work_and_register_copy(self):
        for copied in (False, True):
            with self.subTest(copied=copied):
                pinned, instructions = self.pinned(copied=copied)
                self.assertEqual(recover_block_dispatch(pinned, instructions), [FIRST, SECOND])
                cfg = build_static_cfg(pinned)
                root = cfg["roots"]["interpreter"]
                self.assertTrue({FIRST, SECOND} <= {b["address"] for b in root["blocks"]})
                fresh = extract_fresh_function(pinned, cfg, "interpreter")
                by_address = {o.origin.canonical_address: o for o in fresh.occurrences}
                for address in (FIRST, SECOND):
                    self.assertEqual(by_address[address].origin.function_owners, ("interpreter",))
                    self.assertTrue(any(e.source == address for e in fresh.local_edges))
                jump = instructions[-1]["address"]
                edge, = [e for e in fresh.local_edges if e.source == jump]
                self.assertEqual(edge.summary.target.kind, "symbolic")

    def test_clobbered_table_base_is_not_reused(self):
        pinned, instructions = self.pinned(clobbered=True)
        self.assertEqual(recover_block_dispatch(pinned, instructions), [])

    def test_unbounded_index_is_not_sampled(self):
        pinned, instructions = self.pinned(bounded=False)
        self.assertEqual(recover_block_dispatch(pinned, instructions, max_entries=4), [])

    def test_insufficient_budget_keeps_dispatch_open(self):
        pinned, instructions = self.pinned()
        self.assertEqual(recover_block_dispatch(pinned, instructions, max_entries=1), [])

    def test_full_byte_index_reaches_the_entry_budget(self):
        pinned, instructions = self.pinned(byte_index=True)
        self.assertEqual(recover_block_dispatch(pinned, instructions), [FIRST, SECOND])

    def test_destination_inside_current_block_repartitions_it(self):
        pinned, _ = self.pinned(interior_target=BASE + 7)
        cfg = build_static_cfg(pinned)
        blocks = cfg["roots"]["interpreter"]["blocks"]
        self.assertEqual(blocks[0]["size"], 7)
        self.assertEqual(blocks[0]["successors"], [BASE + 7])
        self.assertIn(BASE + 7, {block["address"] for block in blocks})

    def test_destination_inside_previous_block_repartitions_it(self):
        pinned, _ = self.pinned(interior_target=BASE + 1, earlier_block=True)
        cfg = build_static_cfg(pinned)
        blocks = cfg["roots"]["interpreter"]["blocks"]
        self.assertEqual(blocks[0]["size"], 1)
        self.assertEqual(blocks[0]["successors"], [BASE + 1])
        self.assertIn(BASE + 1, {block["address"] for block in blocks})

    def test_call_at_open_scope_end_retains_its_boundary(self):
        pinned, _ = self.pinned(terminal_call=True)
        root = build_static_cfg(pinned)["roots"]["interpreter"]
        self.assertEqual(root["blocks"][0]["successors"], [])
        self.assertEqual(root["calls"][0]["target"], FIRST)
        self.assertEqual(root["calls"][0]["kind"], "open")

    def test_call_at_strict_scope_end_is_still_rejected(self):
        from extractor.binary_inventory import InventoryError

        pinned, _ = self.pinned(terminal_call=True)
        pinned.manifest["open_transfers"] = False
        with self.assertRaisesRegex(InventoryError, "call fallthrough leaves"):
            build_static_cfg(pinned)


if __name__ == "__main__":
    unittest.main()
