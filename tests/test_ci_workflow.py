import unittest
from pathlib import Path


class CiWorkflowTests(unittest.TestCase):
    def test_python_tests_use_pinned_development_shell(self):
        root = Path(__file__).parents[1]
        workflow = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        flake = (root / "flake.nix").read_text(encoding="utf-8")
        step = workflow.split("- name: Run Python tests in the pinned development shell", 1)[1]
        command = step.split("\n      - name:", 1)[0]
        self.assertIn("nix develop --no-write-lock-file", command)
        self.assertIn("python3 -m pytest tests", command)
        self.assertIn('${ayxg.outPath}/python', flake)


if __name__ == "__main__":
    unittest.main()
