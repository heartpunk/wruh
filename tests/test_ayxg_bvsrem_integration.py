import json
import os
import sys
import unittest
from pathlib import Path

AYXG_SOURCE = Path(os.environ["WRUH_AYXG_SOURCE"])
sys.path.insert(0, str(AYXG_SOURCE / "python"))

from ayxg import BVSort, QFAbvContext, QFAbvExpr, QFAbvValuation, TypedExpr, eval_expr


class AyxgSignedRemainderIntegrationTests(unittest.TestCase):
    def test_pinned_ayxg_matches_its_shared_signed_remainder_vectors(self):
        fixture = json.loads(
            (AYXG_SOURCE / "tests/fixtures/bvsrem.json").read_text()
        )
        self.assertEqual(fixture["operator"], "bv_srem")
        context = QFAbvContext(())

        for case in fixture["cases"]:
            with self.subTest(width=case["width"], left=case["left"], right=case["right"]):
                width = case["width"]
                node = TypedExpr.binary(
                    fixture["operator"],
                    TypedExpr.bv_lit(width, case["left"]),
                    TypedExpr.bv_lit(width, case["right"]),
                )
                expression = QFAbvExpr(context, BVSort(width), node)
                result = eval_expr(expression, QFAbvValuation(context, ()))
                self.assertEqual(result, case["expected"])


if __name__ == "__main__":
    unittest.main()
