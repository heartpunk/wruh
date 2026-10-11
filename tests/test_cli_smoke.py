import subprocess
import unittest


class CliSmokeTest(unittest.TestCase):
    def test_fresh_equivalence_help(self):
        result = subprocess.run(
            ["bazel", "run", "//extractor:fresh_equivalence_tool", "--", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
