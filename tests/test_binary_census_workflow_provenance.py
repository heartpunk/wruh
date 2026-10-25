import re
import unittest
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/binary-census.yml"
CI_SCRIPT = Path(__file__).resolve().parents[1] / "tools/run_census_ci.sh"
BAZEL_TARGETS = Path(__file__).resolve().parents[1] / "extractor/binary_census_targets.bzl"
BAZEL_BUILD = Path(__file__).resolve().parents[1] / "extractor/BUILD.bazel"
TARGETS = ("lua", "quickjs", "cpython", "apache", "node", "bun")
CI_OPTIONS = (
    "--ci-server-url",
    "--ci-repository",
    "--ci-pull-request-number",
    "--ci-pull-request-id",
    "--ci-pull-request-head-repository",
    "--ci-pull-request-head-sha",
    "--ci-run-id",
    "--ci-run-attempt",
    "--ci-checked-out-sha",
    "--ci-workflow",
    "--ci-job",
)
CI_ENV = (
    "WRUH_CI_SERVER_URL",
    "WRUH_CI_REPOSITORY",
    "WRUH_CI_PULL_REQUEST_NUMBER",
    "WRUH_CI_PULL_REQUEST_ID",
    "WRUH_CI_PULL_REQUEST_HEAD_REPOSITORY",
    "WRUH_CI_PULL_REQUEST_HEAD_SHA",
    "WRUH_CI_RUN_ID",
    "WRUH_CI_RUN_ATTEMPT",
    "WRUH_CI_CHECKED_OUT_SHA",
    "WRUH_CI_WORKFLOW",
    "WRUH_CI_JOB",
)


class BinaryCensusWorkflowProvenanceTests(unittest.TestCase):
    def test_every_target_passes_required_ci_provenance(self):
        workflow = WORKFLOW.read_text()
        script = CI_SCRIPT.read_text()
        bazel_targets = BAZEL_TARGETS.read_text()
        bazel_build = BAZEL_BUILD.read_text()

        self.assertIn("run: bash tools/run_census_ci.sh", workflow)
        for name in CI_ENV:
            with self.subTest(workflow_env=name):
                self.assertIn(name, workflow)

        target_match = re.search(r"(?m)^target_ids=\(([^)]*)\)", script)
        self.assertIsNotNone(target_match, "census target list is missing")
        self.assertEqual(tuple(target_match.group(1).split()), TARGETS)
        self.assertIn('for target_id in "${target_ids[@]}"; do', script)
        self.assertIn(
            'bazel_args+=("//extractor:binary_census_${target_id}_remote_test")',
            script,
        )
        target_definitions = re.search(
            r"(?ms)^_CENSUS_REMOTE_TARGETS = \[(.*?)^\]",
            bazel_targets,
        )
        self.assertIsNotNone(target_definitions, "Bazel census target list is missing")
        declared_targets = tuple(
            re.findall(r'\("([a-z0-9]+)"\s*,', target_definitions.group(1))
        )
        self.assertEqual(declared_targets, TARGETS)
        self.assertIn(
            'load(":binary_census_targets.bzl", "binary_census_remote_tests")',
            bazel_build,
        )
        self.assertIn("binary_census_remote_tests()", bazel_build)

    def test_completed_outputs_are_collected_while_bazel_is_running(self):
        script = CI_SCRIPT.read_text()
        self.assertIn("collect_completed_outputs()", script)
        self.assertIn("tools/collect_census_outputs.py", script)
        self.assertIn("tools/write_census_run_manifest.py", script)
        self.assertIn("write_run_manifest \"running\"", script)
        self.assertIn("trap 'stop_collector; collect_completed_outputs; write_run_manifest incomplete' EXIT", script)
        self.assertLess(script.index('while kill -0 "$bazel_pid"'), script.index('collect_completed_outputs\n    sleep 15'))
        self.assertIn("wait \"$collector_pid\"", script)
        self.assertNotIn('kill "$collector_pid"', script)
        self.assertLess(script.index('wait "$bazel_pid"'), script.index('stop_collector\ncollect_completed_outputs'))
        self.assertIn("--nozip_undeclared_test_outputs", script)

        for name, option in zip(CI_ENV, CI_OPTIONS):
            with self.subTest(ci_provenance=name):
                self.assertIn(
                    f'"--test_arg={option}=${{{name}:?{name} is required}}"',
                    script,
                )


if __name__ == "__main__":
    unittest.main()
