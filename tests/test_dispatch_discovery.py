"""Real instruction models recover dispatch across copies and unrelated work."""

import json
import hashlib
import struct
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from extractor.native_runtime import preload_libstdcxx

preload_libstdcxx()

import angr

from extractor.binary_cfg import (
    _assign_discovered_call_blocks, _partition_discovered_blocks, _walk_function,
    build_static_cfg,
)
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

    def relative(self, *, bounded=True, unsigned=False, modified=False, positive=False):
        code = b"\x48\x8d\x15" + struct.pack("<i", TABLE - (BASE + 7))
        code += b"\x48\x89\xf0"  # mov rax, rsi
        if bounded:
            code += b"\x83\xe0\x01"
        if modified:
            value = FIRST - TABLE if modified == "compatible" else 0
            code += (b"\xc7\x07" if modified == "ambiguous" else b"\xc7\x02")
            code += struct.pack("<i", value)
        code += b"\x8b\x04\x82" if unsigned else b"\x48\x63\x04\x82"
        code += b"\x48\x01\xd0\xff\xe0"
        raw = bytearray(b"\x90" * 0x110)
        raw[:len(code)] = code
        raw[0x100:0x108] = struct.pack("<ii", FIRST - TABLE, 8 if positive else SECOND - TABLE)
        project = angr.load_shellcode(bytes(raw), arch="amd64", load_address=BASE)
        instructions = [{"address": item.address} for item in project.arch.capstone.disasm(code, BASE)]
        return PinnedBinary(Path(self.temporary.name) / "relative.bin", {}, project), instructions

    def test_relative_signed_offsets_and_budgets(self):
        pinned, instructions = self.relative()
        self.assertEqual(recover_block_dispatch(pinned, instructions), [FIRST, SECOND])
        self.assertEqual(recover_block_dispatch(pinned, instructions, max_entries=1), [])
        pinned, instructions = self.relative(positive=True)
        self.assertEqual(recover_block_dispatch(pinned, instructions), [FIRST, TABLE + 8])
        pinned, instructions = self.relative(bounded=False)
        self.assertEqual(recover_block_dispatch(pinned, instructions), [])

    def test_relative_unsigned_load_remains_open(self):
        pinned, instructions = self.relative(unsigned=True)
        self.assertEqual(recover_block_dispatch(pinned, instructions), [])

    def test_relative_store_feasibility(self):
        for modification, expected in (
            (True, [SECOND]),  # The overwritten first entry is incompatible.
            ("compatible", [FIRST, SECOND]),
            ("ambiguous", [FIRST, SECOND]),  # Nonaliasing witnesses exist.
        ):
            with self.subTest(modification=modification):
                pinned, instructions = self.relative(modified=modification)
                self.assertEqual(recover_block_dispatch(pinned, instructions), expected)

    def test_qemu_actual_relative_table(self):
        fixture_path = Path(__file__).parent / "fixtures/qemu-11.1.2-relative-dispatch/fixture.json"
        data = json.loads(fixture_path.read_text())
        code = bytes.fromhex(data["code_hex"])
        table = bytes.fromhex(data["table_hex"])
        raw = bytearray(data["table"] - data["entry"] + len(table))
        raw[:len(code)] = code
        raw[-len(table):] = table
        project = angr.load_shellcode(bytes(raw), arch="amd64", load_address=data["entry"])
        instructions = [{"address": item.address} for item in project.arch.capstone.disasm(code, data["entry"])]
        pinned = PinnedBinary(fixture_path, {}, project)
        self.assertEqual(recover_block_dispatch(pinned, instructions), sorted(data["targets"]))

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

    def test_split_call_owner_uses_instruction_boundaries_with_overlap(self):
        blocks = [
            {"address": BASE, "size": 4,
             "instructions": [{"address": BASE, "size": 4}], "successors": []},
            {"address": BASE + 1, "size": 3,
             "instructions": [{"address": BASE + 1, "size": 1},
                              {"address": BASE + 2, "size": 2}], "successors": []},
        ]
        partitioned = _partition_discovered_blocks(blocks, {BASE + 2})
        calls = [{"address": BASE + 2, "block": BASE + 1, "target": FIRST}]
        _assign_discovered_call_blocks(partitioned, calls)
        self.assertEqual(calls[0]["block"], BASE + 2)

    def test_discovered_boundary_preserves_call_ownership(self):
        pinned, _ = self.pinned(interior_target=BASE + 7)
        raw = bytearray(pinned.artifact.read_bytes())
        raw[0x40:0x46] = b"\xe8" + struct.pack("<i", SECOND - (FIRST + 5)) + b"\xc3"
        # Keep both the interior split and a reachable call in the dispatch table.
        struct.pack_into("<Q", raw, 0x108, FIRST)
        pinned.artifact.write_bytes(raw)
        project = angr.load_shellcode(bytes(raw), arch="amd64", load_address=BASE)
        manifest = {**pinned.manifest, "image_sha256": hashlib.sha256(raw).hexdigest()}
        pinned = PinnedBinary(pinned.artifact, manifest, project)
        _, calls, _ = _walk_function(
            pinned, root_name="interpreter", root=pinned.manifest["roots"]["interpreter"],
            jump_tables={},
        )
        call, = calls
        self.assertEqual(call["address"], FIRST)
        self.assertEqual(call["block"], FIRST)
        self.assertEqual(call["target"], SECOND)

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

    def test_identical_suffix_from_implicit_block_split_is_shared(self):
        instructions = [{"address": BASE + index, "size": 1, "bytes": "90"}
                        for index in range(4)]
        blocks = [
            {"address": BASE, "size": 4, "instructions": instructions,
             "successors": [FIRST]},
            {"address": BASE + 2, "size": 2, "instructions": instructions[2:],
             "successors": [SECOND]},
        ]
        partitioned = _partition_discovered_blocks(blocks, {BASE + 1})
        self.assertEqual([b["address"] for b in partitioned], [BASE, BASE + 1, BASE + 2])
        self.assertEqual([b["size"] for b in partitioned], [1, 1, 2])
        self.assertEqual(partitioned[-1]["successors"], [FIRST, SECOND])
        self.assertEqual(sum(len(b["instructions"]) for b in partitioned), 4)


if __name__ == "__main__":
    unittest.main()
