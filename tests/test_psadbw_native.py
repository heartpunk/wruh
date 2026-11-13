"""Compare the extracted PSADBW relation to the actual x86-64 instruction."""
import ctypes
import hashlib
import json
import mmap
import platform
import random
import tempfile
import unittest
from pathlib import Path

from extractor.native_runtime import preload_libstdcxx

preload_libstdcxx()
import z3
from ayxg.z3 import declaration_variables, expr_to_z3

from extractor import runtime
from extractor.binary_cfg import build_static_cfg
from extractor.binary_inventory import PinnedBinary
from extractor.fresh import FreshFunction, extract_fresh_function


@unittest.skipUnless(platform.system() == "Linux" and platform.machine() == "x86_64", "native x86-64 Linux required")
class PsadbwNativeTest(unittest.TestCase):
    def test_extracted_xmm_psadbw_matches_native_instruction(self):
        pc = 0x400000
        raw = bytes.fromhex("660ff6c1c3")  # psadbw xmm0, xmm1; ret
        digest = hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "psadbw.bin"
            artifact.write_bytes(raw)
            project = runtime.angr.load_shellcode(raw, arch="amd64", load_address=pc)
            manifest = {
                "image_sha256": digest,
                "roots": {"fixture": {"address": pc, "size": len(raw), "symbol": "fixture"}},
                "primitive_boundaries": {},
                "call_graph": {"fixture": {}},
                "open_transfers": True,
            }
            pinned = PinnedBinary(artifact, manifest, project)
            cfg = build_static_cfg(pinned)
            fresh = extract_fresh_function(pinned, cfg, "fixture")
            model = FreshFunction.from_data(json.loads(fresh.canonical_json()))
        edge, = [edge for edge in model.local_edges if edge.source == pc]
        self.assertEqual(edge.summary.target.value, pc + 4)
        ctx = z3.Context()
        variables = declaration_variables(model.declarations, ctx)
        update = next(a for a in edge.summary.simultaneous_update if a.name == "zmm0")
        expression = expr_to_z3(update.value, variables, ctx)

        # movdqu xmm0,[rdi]; movdqu xmm1,[rsi]; psadbw xmm0,xmm1;
        # movdqu [rdx],xmm0; ret.  The instruction under test is identical.
        wrapper = bytes.fromhex("f30f6f07f30f6f0e660ff6c1f30f7f02c3")
        with mmap.mmap(-1, len(wrapper), prot=mmap.PROT_READ | mmap.PROT_WRITE | mmap.PROT_EXEC) as page:
            page.write(wrapper)
            invoke = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(
                ctypes.addressof(ctypes.c_char.from_buffer(page))
            )
            rng = random.Random(0x5AD8)
            cases = [(0, 0), ((1 << 128) - 1, 0), (0, (1 << 128) - 1)]
            cases.extend((rng.getrandbits(128), rng.getrandbits(128)) for _ in range(32))
            for left, right in cases:
                with self.subTest(left=hex(left), right=hex(right)):
                    x = (ctypes.c_ubyte * 16).from_buffer_copy(left.to_bytes(16, "little"))
                    y = (ctypes.c_ubyte * 16).from_buffer_copy(right.to_bytes(16, "little"))
                    observed = (ctypes.c_ubyte * 16)()
                    invoke(x, y, observed)
                    native = int.from_bytes(bytes(observed), "little")
                    actual = z3.simplify(z3.substitute(
                        expression,
                        (variables["zmm0"], z3.BitVecVal(left, 512, ctx=ctx)),
                        (variables["zmm1"], z3.BitVecVal(right, 512, ctx=ctx)),
                    ))
                    self.assertTrue(z3.is_bv_value(actual), str(actual))
                    self.assertEqual(actual.as_long() & ((1 << 128) - 1), native)


if __name__ == "__main__":
    unittest.main()
