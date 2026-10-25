import json
import subprocess
import sys
import unittest
from pathlib import Path

from tools.write_census_run_manifest import build_manifest


class CensusRunManifestTests(unittest.TestCase):
    def test_empty_collected_targets_are_an_empty_array(self):
        manifest = build_manifest(
            wruh_revision="abc123",
            run_id="123",
            run_attempt="2",
            requested_targets=("lua", "node"),
            collected_targets=(),
            status="running",
        )
        self.assertEqual(manifest["collectedTargets"], [])
        self.assertEqual(manifest["requestedTargets"], ["lua", "node"])

    def test_cli_serializes_empty_collected_targets_as_an_empty_array(self):
        script = Path(__file__).resolve().parents[1] / "tools/write_census_run_manifest.py"
        result = subprocess.run(
            [
                sys.executable,
                str(script),
                "--wruh-revision", "abc123",
                "--run-id", "123",
                "--run-attempt", "2",
                "--requested-targets", "lua", "node",
                "--collected-targets",
                "--status", "running",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(json.loads(result.stdout)["collectedTargets"], [])


if __name__ == "__main__":
    unittest.main()
