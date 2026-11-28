import os
import subprocess
import sys
import unittest
from pathlib import Path


class CliSmokeTest(unittest.TestCase):
    def test_extractor_cli_help(self):
        # Bazel initializes sys.path in its launcher; a raw interpreter child
        # needs those declared import roots too, with PYTHONSAFEPATH retained.
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(
            str(Path(path).absolute()) for path in sys.path if path
        )
        result = subprocess.run(
            [sys.executable, "-m", "extractor.extract_cli", "--help"],
            cwd=Path(__file__).parents[1],
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("--artifact", result.stdout)
        for option in ("--objects", "--data-intervals", "--chunk-size", "--seed"):
            self.assertIn(option, result.stdout)

