"""PAUSE is a sequential fallthrough, not a general Yield rewrite."""
import unittest
from pathlib import Path
from unittest.mock import patch

from extractor import runtime
from extractor.binary_cfg import _is_amd64_pause_yield, _walk_function
from extractor.binary_inventory import InventoryError, PinnedBinary


class PauseYieldTest(unittest.TestCase):
    def test_only_exact_amd64_pause_with_matching_fallthrough_is_accepted(self):
        instruction = {"mnemonic": "pause", "bytes": "f390", "size": 2, "address": 0x1000}
        self.assertTrue(_is_amd64_pause_yield("AMD64", "Ijk_Yield", [instruction], 0x1002, 0x1002))
        cases = [
            ("ARM64", "Ijk_Yield", [instruction], 0x1002, 0x1002),
            ("AMD64", "Ijk_Boring", [instruction], 0x1002, 0x1002),
            ("AMD64", "Ijk_Yield", [], 0x1002, 0x1002),
            ("AMD64", "Ijk_Yield", [{**instruction, "bytes": "9090"}], 0x1002, 0x1002),
            ("AMD64", "Ijk_Yield", [{**instruction, "mnemonic": "other"}], 0x1002, 0x1002),
            ("AMD64", "Ijk_Yield", [instruction], 0x1002, 0x1004),
            ("AMD64", "Ijk_Yield", [instruction], 0x1003, 0x1003),
        ]
        for args in cases:
            with self.subTest(args=args):
                self.assertFalse(_is_amd64_pause_yield(*args))

    def test_unknown_yield_remains_rejected_by_cfg(self):
        address = 0x400000
        project = runtime.angr.load_shellcode(b"\x90\xc3", arch="amd64", load_address=address)
        original_block = project.factory.block

        def yield_non_pause(*args, **kwargs):
            block = original_block(*args, **kwargs)
            block.vex.jumpkind = "Ijk_Yield"
            return block

        pinned = PinnedBinary(Path("<synthetic-yield>"), {"open_transfers": True}, project)
        with patch.object(project.factory, "block", side_effect=yield_non_pause):
            with self.assertRaisesRegex(InventoryError, "unsupported jumpkind.*Ijk_Yield"):
                _walk_function(
                    pinned, root_name="unknown",
                    root={"address": address, "size": 2}, jump_tables={},
                )

    def test_pause_at_boundary_respects_open_transfer_policy(self):
        address = 0x400000
        project = runtime.angr.load_shellcode(b"\xf3\x90", arch="amd64", load_address=address)
        for open_transfers in (False, True):
            pinned = PinnedBinary(Path("<pause>"), {"open_transfers": open_transfers}, project)
            args = dict(root_name="pause", root={"address": address, "size": 2}, jump_tables={})
            with self.subTest(open_transfers=open_transfers):
                if open_transfers:
                    blocks, _, _ = _walk_function(pinned, **args)
                    self.assertEqual(blocks[0]["successors"], [])
                    self.assertEqual(blocks[0]["instructions"][-1]["mnemonic"], "pause")
                else:
                    with self.assertRaisesRegex(InventoryError, "PAUSE fallthrough leaves"):
                        _walk_function(pinned, **args)


if __name__ == "__main__":
    unittest.main()
