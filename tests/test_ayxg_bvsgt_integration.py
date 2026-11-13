"""The pinned AYXG bvsgt vectors pass through WRUH's Z3 importer."""
import json
import os
import sys
import unittest
from pathlib import Path

AYXG_SOURCE = Path(os.environ["WRUH_AYXG_SOURCE"])
sys.path.insert(0, str(AYXG_SOURCE / "python"))

import z3
from ayxg.z3 import expr_from_z3, expr_to_z3


class AyxgSignedGreaterThanIntegrationTests(unittest.TestCase):
    def test_z3_signed_greater_import_matches_pinned_ayxg_vectors(self):
        fixture = json.loads(
            (AYXG_SOURCE / "tests/fixtures/bvsgt_cases.json").read_text()
        )
        self.assertEqual(fixture["encoding"], "ayxg-bvsgt-cases-v1")
        self.assertEqual(fixture["resultDatatype"], "boolean")
        self.assertTrue(fixture["cases"])

        for case in fixture["cases"]:
            width = case["width"]
            with self.subTest(width=width, lhs=case["lhs"], rhs=case["rhs"]):
                lhs = z3.BitVec("bvsgt_lhs", width)
                rhs = z3.BitVec("bvsgt_rhs", width)
                # Z3 represents signed greater-than as reversed signed less-than.
                imported = expr_from_z3(lhs > rhs)
                variables = {"bvsgt_lhs": lhs, "bvsgt_rhs": rhs}
                round_trip = expr_to_z3(imported, variables, lhs.ctx)
                actual = z3.simplify(z3.substitute(
                    round_trip,
                    (lhs, z3.BitVecVal(case["lhs"], width, ctx=lhs.ctx)),
                    (rhs, z3.BitVecVal(case["rhs"], width, ctx=lhs.ctx)),
                ))
                self.assertEqual(z3.is_true(actual), case["result"])


if __name__ == "__main__":
    unittest.main()
