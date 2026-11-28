"""Equanimity operations requested by the Lean fresh-extraction driver.

One JSON line is returned for the inventory, then one for each requested
instruction. This process never assembles STS edges or a fresh artifact.
"""

from __future__ import annotations

import argparse
import json
import sys

from extractor.backend import Session
from extractor.extraction_args import add_arguments
from extractor.linear_pipeline import prepare


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    return parser.parse_args()


def _inventory(args: argparse.Namespace):
    session, records, report, image_sha256 = prepare(args)
    sites = [{"address": address, "occurrence": occurrence.to_data()} for address, occurrence in records]
    inventory = {
        "kind": "inventory", "image_sha256": image_sha256, "inventory": report,
        "declarations": [declaration.to_data() for declaration in session.image.declarations],
        "architecture": session.image.architecture,
        "sites": sites,
        "loaded_image": session.image.loaded_image,
    }
    return session, inventory, {address for address, _ in records}


def _step(session: Session, address: int) -> dict:
    return session.step(address).to_data()


def main() -> int:
    session, inventory, sites = _inventory(_arguments())
    print(json.dumps(inventory, separators=(",", ":")), flush=True)
    for line in sys.stdin:
        request = json.loads(line)
        if request.get("op") == "quit":
            return 0
        if request.get("op") != "step" or request.get("address") not in sites:
            raise ValueError("unknown instruction request")
        print(json.dumps(_step(session, request["address"]), separators=(",", ":")), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
