import re
import unittest
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/binary-census.yml"
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
        content = WORKFLOW.read_text()
        sections = re.split(r"(?m)^  ([a-z][a-z0-9_-]*):\s*$", content)
        jobs = dict(zip(sections[1::2], sections[2::2]))

        for target in TARGETS:
            with self.subTest(target=target):
                self.assertIn(target, jobs)
                block = jobs[target]
                step_start = block.index("- name: Run generic binary census")
                step_end = block.index("- uses: actions/upload-artifact", step_start)
                run_step = block[step_start:step_end]

                for option in CI_OPTIONS:
                    self.assertIn(option, run_step)
                for name in CI_ENV:
                    self.assertIn(name, run_step)


if __name__ == "__main__":
    unittest.main()
