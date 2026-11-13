"""Exercise recovered CFG scope using short AMD64 instruction fixtures."""

import io
from types import SimpleNamespace
import unittest

import angr

from extractor.binary_cfg import _walk_function
from extractor.binary_inventory import InventoryError


class CfgExtentTests(unittest.TestCase):
    ENTRY = 0x400000

    def walk(self, code, size, *, ranges=None, open_transfers=True):
        project = angr.Project(
            io.BytesIO(code),
            main_opts={
                "backend": "blob",
                "arch": "amd64",
                "base_addr": self.ENTRY,
                "entry_point": self.ENTRY,
            },
            auto_load_libs=False,
        )
        root = {"address": self.ENTRY, "size": size}
        if ranges is not None:
            root["code_ranges"] = [
                [self.ENTRY + start, self.ENTRY + end] for start, end in ranges
            ]
        return _walk_function(
            SimpleNamespace(project=project, manifest={"open_transfers": open_transfers}),
            root_name="fixture",
            root=root,
            jump_tables={},
        )

    def test_final_nop_is_bounded_before_adjacent_function(self):
        blocks, calls, indirect = self.walk(b"\x90\xc3", 1)
        self.assertEqual([i["bytes"] for i in blocks[0]["instructions"]], ["90"])
        self.assertEqual(blocks[0]["successors"], [])
        self.assertEqual((calls, indirect), ([], set()))

    def test_strict_scope_rejects_external_fallthrough(self):
        with self.assertRaisesRegex(InventoryError, "edge leaves function"):
            self.walk(b"\x90\xc3", 1, open_transfers=False)

    def test_jump_across_gap_reaches_later_recovered_range(self):
        # JMP to RET over UD2 and NOP bytes that are outside recovered scope.
        blocks, _, _ = self.walk(
            b"\xeb\x03\x0f\x0b\x90\xc3", 6, ranges=[(0, 2), (5, 6)]
        )
        self.assertEqual([b["address"] for b in blocks], [self.ENTRY, self.ENTRY + 5])
        self.assertEqual(blocks[0]["successors"], [self.ENTRY + 5])
        self.assertEqual([b["instructions"][0]["bytes"] for b in blocks], ["eb03", "c3"])

    def test_fallthrough_into_gap_is_open_not_invented_code(self):
        blocks, _, _ = self.walk(b"\x90\x0f\x0b\xc3", 4, ranges=[(0, 1), (3, 4)])
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["successors"], [])
        with self.assertRaisesRegex(InventoryError, "edge leaves function"):
            self.walk(b"\x90\x0f\x0b\xc3", 4, ranges=[(0, 1), (3, 4)], open_transfers=False)

    def test_partial_instruction_at_extent_is_not_accepted(self):
        # The last two bytes exist in the file, but lie outside the scope.
        with self.assertRaises(InventoryError):
            self.walk(b"\xb8\x01\x00\x00\x00\xc3", 3)

    def test_range_must_include_entry_and_stay_in_extent(self):
        for ranges in ([(1, 2)], [(0, 3)], []):
            with self.subTest(ranges=ranges), self.assertRaises(InventoryError):
                self.walk(b"\x90\xc3", 2, ranges=ranges)


if __name__ == "__main__":
    unittest.main()
