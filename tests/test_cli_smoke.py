import subprocess
import sys
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
