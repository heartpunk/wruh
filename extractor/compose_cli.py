"""Compose exported fresh STSes without loading or executing a binary."""
from __future__ import annotations

from extractor.runtime_trace import start_runtime_trace

start_runtime_trace()
import argparse
from pathlib import Path

from ayxg.codec import dumps, loads

from extractor.native_runtime import preload_libstdcxx

_LIBSTDCXX = preload_libstdcxx()
from extractor.artifact import LocalEdge
from extractor.fresh import FreshFunction
from extractor.fresh_composition import compose_fresh_paths


def compose(data: dict, *, max_steps: int = 4096, max_paths: int = 4096) -> dict:
    if data.get("schema") != "wruh-fresh-bundle-v1":
        raise ValueError("unknown fresh bundle schema")
    functions = tuple(FreshFunction.from_data(item) for item in data["functions"])
    paths = compose_fresh_paths(data["cfg"], functions, data["root_id"],
        tuple(LocalEdge.from_data(item) for item in data["external_edges"]),
        max_steps=max_steps, max_paths=max_paths)
    return {"schema": "wruh-composed-paths-v1", "root_id": data["root_id"],
        "image_sha256": data["image_sha256"],
        "paths": [{"run_id": path.run_id, "guard": path.guard.to_data(),
            "update": {name: value.to_data() for name, value in path.update.items()},
            "target": path.target.to_data(), "edge_ids": [list(edge) for edge in path.edge_ids]}
            for path in paths]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-steps", type=int, default=4096)
    parser.add_argument("--max-paths", type=int, default=4096)
    args = parser.parse_args()
    args.output.write_text(dumps(compose(loads(args.input.read_text()),
        max_steps=args.max_steps, max_paths=args.max_paths), indent=2, sort_keys=True) + "\n")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
