import json
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from extractor import binary_census


class BuildProvenanceTests(unittest.TestCase):
    def _arguments(self, **overrides):
        values = {
            "build_package": None,
            "build_output": None,
            "nixpkgs_revision": None,
            "nix_version": None,
            "build_configuration": None,
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    def _provenance(self, arguments):
        return binary_census._build_provenance(
            arguments,
            census_id="urn:test:census",
            image_id="urn:test:image",
            binary_id="urn:test:binary",
            target_release_id="urn:test:target-release",
        )

    def test_cli_defaults_leave_build_provenance_unknown(self):
        argv = [
            "binary_census",
            "--binary", "input.bin",
            "--target-id", "generic",
            "--target-version", "1",
            "--output-dir", "out",
        ]
        with (
            patch.object(sys, "argv", argv),
            patch.object(binary_census, "_is_github_actions_runner", return_value=False),
            patch.object(binary_census, "_configure_logging"),
            patch.object(binary_census, "run", return_value=0) as run,
        ):
            self.assertEqual(binary_census.main(), 0)

        arguments = run.call_args.args[0]
        self.assertIsNone(arguments.build_package)
        self.assertIsNone(arguments.build_output)
        self.assertIsNone(arguments.nixpkgs_revision)
        self.assertIsNone(arguments.nix_version)
        self.assertIsNone(arguments.build_configuration)

        image_properties, tool_releases, build_node = self._provenance(arguments)
        self.assertEqual(image_properties, {})
        self.assertEqual(tool_releases, [])
        self.assertIsNone(build_node)
        serialized = json.dumps([image_properties, tool_releases, build_node])
        self.assertNotIn("Nix", serialized)
        self.assertNotIn("dontStrip", serialized)

    def test_explicit_ci_metadata_preserves_nix_build_lineage(self):
        arguments = self._arguments(
            build_package="python3",
            build_output="/nix/store/example-python3",
            nixpkgs_revision="0123456789abcdef",
            nix_version="2.24.0",
            build_configuration="Nix package built with symbol tables retained (dontStrip=true)",
        )

        image_properties, tool_releases, build_node = self._provenance(arguments)

        self.assertEqual(image_properties["bfe:distributionRevision"], "0123456789abcdef")
        self.assertIn("dontStrip=true", image_properties["bfe:targetBuildConfiguration"])
        self.assertEqual({node["bfe:toolName"] for _, node in tool_releases}, {"Nix", "Nixpkgs"})
        self.assertIsNotNone(build_node)
        self.assertEqual(build_node["@type"], "bfe:BuildActivity")
        self.assertEqual(build_node["bfe:identifier"], ["python3", "/nix/store/example-python3"])
        self.assertEqual(build_node["bfe:buildUsesInput"][0]["@id"], "urn:wruh:tool:nixpkgs:0123456789abcdef")
        self.assertEqual(build_node["bfe:activityUsesToolRelease"]["@id"], "urn:wruh:tool:nix:2-24-0")


if __name__ == "__main__":
    unittest.main()
