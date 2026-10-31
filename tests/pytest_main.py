"""Bazel entry point for the same pytest suite run outside Bazel."""
from pathlib import Path

import pytest

if __name__ == "__main__":
    raise SystemExit(pytest.main([str(Path(__file__).parent), "-v"]))
