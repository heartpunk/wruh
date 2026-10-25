import unittest
from pathlib import Path

from extractor.ontology_selector import build_selection_manifest, canonical_inventory, load_records, read_hypothesis


class OntologySelectorTests(unittest.TestCase):
    kind = "https://github.com/heartpunk/wruh/blob/main/docs/ontology/wruh.ttl#failureUnsupportedOperation"

    def inventory(self):
        return canonical_inventory(target_id="lua", binary_sha256="a" * 64, architecture="AMD64",
                                   policy_version="symbols-v1",
                                   candidates=[{"candidateId": f"fn_{i:016x}", "addressSpace": "object-relative",
                                                "address": i, "extent": 16} for i in range(1, 5)])

    def test_positive_match_and_seeded_unaffected_sample(self):
        inventory = self.inventory()
        records = [{"binarySha256": "a" * 64, "candidateId": "fn_0000000000000001",
                    "failureKind": self.kind, "evidenceState": "known", "evidenceReference": "archive:report#entry-1"}]
        result = build_selection_manifest(inventory, {self.kind}, records, history_coverage_complete=True,
                                          seed=19, sample_size=1)
        manifest = result["manifest"]
        self.assertEqual(manifest["mode"], "explicit")
        self.assertEqual(manifest["candidateIds"][0], "fn_0000000000000001")
        self.assertIn(manifest["candidateIds"][1], {"fn_0000000000000002", "fn_0000000000000003", "fn_0000000000000004"})
        self.assertEqual(manifest["inventoryDigest"][:7], "sha256:")
        self.assertEqual(result, build_selection_manifest(inventory, {self.kind}, records,
                                                          history_coverage_complete=True, seed=19, sample_size=1))

    def test_missing_evidence_stays_unknown_and_is_not_success(self):
        record = {"binarySha256": "a" * 64, "candidateId": "fn_0000000000000001",
                  "failureKind": self.kind, "evidenceState": "unknown", "evidenceReference": None}
        result = build_selection_manifest(self.inventory(), {self.kind}, [record],
                                          history_coverage_complete=False, seed=1, sample_size=1)
        self.assertEqual(result["manifest"]["mode"], "all")
        self.assertEqual(result["manifest"]["candidateIds"], [])
        self.assertIn("historical-evidence-unmapped-or-unknown", result["manifest"]["evidenceGaps"])

    def test_example_turtle_hypothesis_names_a_known_typed_mechanism(self):
        path = Path(__file__).resolve().parents[1] / "docs/ontology/pr-hypothesis-example.ttl"
        self.assertEqual(read_hypothesis(path), {self.kind})

    def test_missing_archive_falls_back_to_complete_binary_census(self):
        records, gaps = load_records([Path("/path/that/does/not/exist.jsonld")])
        result = build_selection_manifest(self.inventory(), {self.kind}, records,
                                          history_coverage_complete=False, seed=2, sample_size=1,
                                          evidence_gaps=gaps)
        self.assertEqual(result["manifest"]["mode"], "all")
        self.assertEqual(result["manifest"]["candidateIds"], [])
        self.assertEqual(result["manifest"]["evidenceGaps"], ["exist.jsonld:unknown"])


if __name__ == "__main__":
    unittest.main()
