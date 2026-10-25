import json
import tempfile
import unittest
from pathlib import Path

from tools.collect_census_outputs import collect


class CensusOutputCollectionTests(unittest.TestCase):
    def test_copies_only_sealed_targets_and_preserves_shard_directories(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            testlogs = root / "bazel-testlogs"
            reports = root / "reports"
            complete = testlogs / "extractor/binary_census_node_remote_test/test.outputs/shard_1"
            complete.mkdir(parents=True)
            (complete / "summary.json").write_text(json.dumps({"attempted": 3}))
            (complete / "entries.jsonl").write_text('{"candidate":"fn_1"}\n')
            (complete / "census.jsonld").write_text(json.dumps({"@graph": [
                {"bfe:identifier": "github-actions-run:123/attempt/2"},
                {"bfe:identifier": "git-commit:abc123"},
            ]}))
            stale = testlogs / "extractor/binary_census_bun_remote_test/test.outputs"
            stale.mkdir(parents=True)
            (stale / "summary.json").write_text(json.dumps({"attempted": 8}))
            (stale / "census.jsonld").write_text(json.dumps({"@graph": [
                {"bfe:identifier": "github-actions-run:old/attempt/1"},
                {"bfe:identifier": "git-commit:abc123"},
            ]}))

            self.assertEqual(collect(
                testlogs,
                reports,
                run_identifier="github-actions-run:123/attempt/2",
                revision_identifier="git-commit:abc123",
            ), {"node"})
            copied = reports / "node/shard_1"
            self.assertEqual(json.loads((copied / "summary.json").read_text())["attempted"], 3)
            self.assertTrue((copied / ".collected").exists())
            self.assertFalse((reports / "bun").exists())

            (complete / "entries.jsonl").write_text("later mutation\n")
            self.assertEqual(collect(
                testlogs,
                reports,
                run_identifier="github-actions-run:123/attempt/2",
                revision_identifier="git-commit:abc123",
            ), set())
            self.assertEqual((copied / "entries.jsonl").read_text(), '{"candidate":"fn_1"}\n')


if __name__ == "__main__":
    unittest.main()
