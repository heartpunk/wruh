import unittest
from pathlib import Path


class CiWorkflowTests(unittest.TestCase):
    def test_python_test_command_exposes_ayxg_source(self):
        workflow = Path(__file__).parents[1] / ".github" / "workflows" / "ci.yml"
        source = workflow.read_text(encoding="utf-8")
        test_step = source.split(
            "- name: Run Python tests in the pinned development shell", 1
        )[1]
        command = test_step.split("\n      - name:", 1)[0]

        self.assertIn('PYTHONPATH="$GITHUB_WORKSPACE:$WRUH_AYXG_SOURCE/python', command)
        self.assertIn('exec python3 -m unittest discover', command)


if __name__ == "__main__":
    unittest.main()
