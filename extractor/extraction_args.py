"""Arguments shared by the Python and Lean extraction entry points."""
from __future__ import annotations

import argparse
from pathlib import Path


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--objects", type=Path, help="explicit object-set JSON paths and base addresses")
    parser.add_argument("--data-intervals", type=Path, help="JSON array of half-open start/end address objects")
    parser.add_argument("--chunk-size", type=int, default=256)
    parser.add_argument("--scope-bytes", type=int, help="limit instruction starts to this many bytes from each object’s first executable segment")
    parser.add_argument("--seed", type=int, default=0)
