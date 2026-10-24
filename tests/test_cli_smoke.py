import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from extractor import binary_census


class CliSmokeTest(unittest.TestCase):
    def test_extractor_cli_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "extractor.extract_cli", "--help"],
            cwd=Path(__file__).parents[1],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("--artifact", result.stdout)

    def test_ci_metadata_arguments_are_linked_in_jsonld(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            binary = temporary_path / "input.bin"
            binary.write_bytes(b"metadata integration fixture")
            output_dir = temporary_path / "out"
            argv = [
                "binary_census",
                "--binary", str(binary),
                "--target-id", "lua",
                "--target-version", "5.5.1",
                "--output-dir", str(output_dir),
                "--ci-server-url", "https://github.com",
                "--ci-repository", "heartpunk/wruh",
                "--ci-pull-request-number", "73",
                "--ci-pull-request-id", "987654321",
                "--ci-pull-request-head-repository", "contributor/wruh",
                "--ci-pull-request-head-sha", "a" * 40,
                "--ci-run-id", "1234567890",
                "--ci-run-attempt", "2",
                "--ci-checked-out-sha", "b" * 40,
                "--ci-workflow", "Binary function census",
                "--ci-job", "lua",
            ]
            image = SimpleNamespace(binary=str(binary), symbols=[])
            project = SimpleNamespace(
                arch=SimpleNamespace(name="AMD64", bits=64),
                loader=SimpleNamespace(main_object=image),
            )

            def fake_project_factory(*_args, **_kwargs):
                return project

            def fake_noop(*_args, **_kwargs):
                return None

            fake_angr = ModuleType("angr")
            fake_angr.Project = fake_project_factory
            fake_native_runtime = ModuleType("extractor.native_runtime")
            fake_native_runtime.preload_libstdcxx = fake_noop
            fake_amd64_state = ModuleType("extractor.amd64_state")
            fake_amd64_state.clear_smt_translation_cache = fake_noop
            fake_binary_cfg = ModuleType("extractor.binary_cfg")
            fake_binary_cfg.build_static_cfg = fake_noop
            fake_binary_inventory = ModuleType("extractor.binary_inventory")
            fake_binary_inventory.PinnedBinary = object
            fake_fresh = ModuleType("extractor.fresh")
            fake_fresh.extract_fresh_function = fake_noop
            fake_modules = {
                "angr": fake_angr,
                "extractor.native_runtime": fake_native_runtime,
                "extractor.amd64_state": fake_amd64_state,
                "extractor.binary_cfg": fake_binary_cfg,
                "extractor.binary_inventory": fake_binary_inventory,
                "extractor.fresh": fake_fresh,
            }
            with (
                patch.object(sys, "argv", argv),
                patch.object(binary_census, "_configure_logging"),
                patch.dict(sys.modules, fake_modules),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(binary_census.main(), 0)

            report_path = output_dir / "census.jsonld"
            report = json.loads(report_path.read_text(encoding="utf-8"))

        by_id = {node["@id"]: node for node in report["@graph"]}
        pull_request_url = "https://github.com/heartpunk/wruh/pull/73"
        run_url = "https://github.com/heartpunk/wruh/actions/runs/1234567890/attempts/2"
        head_commit_url = f"https://github.com/contributor/wruh/commit/{'a' * 40}"
        checked_out_commit_url = f"https://github.com/heartpunk/wruh/commit/{'b' * 40}"
        census_node = next(node for node in report["@graph"] if node.get("@type") == "bfe:ExtractionCensus")
        self.assertEqual(
            by_id[pull_request_url]["bfe:identifier"],
            ["github-pull-request-number:73", "github-pull-request-id:987654321"],
        )
        self.assertEqual(by_id[run_url]["bfe:identifier"], "github-actions-run:1234567890/attempt/2")
        self.assertEqual(by_id[pull_request_url]["@type"], "prov:Entity")
        self.assertEqual(by_id[run_url]["@type"], "prov:Activity")
        self.assertEqual(census_node["prov:wasInformedBy"], {"@id": run_url})
        self.assertEqual(
            report["@context"]["prov:wasInformedBy"],
            {"@id": "prov:wasInformedBy", "@type": "@id"},
        )
        self.assertEqual(
            {reference["@id"] for reference in by_id[run_url]["prov:used"]},
            {pull_request_url, head_commit_url, checked_out_commit_url},
        )
        self.assertIn({"@id": pull_request_url}, census_node["prov:used"])
        self.assertIn("workflow Binary function census, job lua", by_id[run_url]["rdfs:label"])


if __name__ == "__main__":
    unittest.main()
