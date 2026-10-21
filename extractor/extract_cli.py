"""Export fresh STSes and their CFG for later composition."""

from __future__ import annotations

from extractor.runtime_trace import start_runtime_trace

start_runtime_trace()

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


def _provider(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("wruh_abi_provider", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load ABI provider from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    provider = getattr(module, "PROVIDER", None)
    if provider is None:
        raise ValueError("ABI provider module must export PROVIDER")
    return provider


def _root_closure(cfg: dict[str, Any], root_id: str) -> tuple[str, ...]:
    if root_id not in cfg["roots"]:
        raise ValueError(f"unknown root {root_id!r}")
    selected = {root_id}
    pending = [root_id]
    while pending:
        current = pending.pop()
        for call in cfg["roots"][current].get("calls", ()):
            if call["kind"] == "direct-local" and call["name"] not in selected:
                selected.add(call["name"])
                pending.append(call["name"])
    return tuple(sorted(
        selected,
        key=lambda name: (cfg["roots"][name]["address"], name),
    ))


def _run(arguments: argparse.Namespace) -> dict[str, Any]:
    # Delay the extraction stack until after argparse has handled --help. This
    # keeps the CLI entrypoint inspectable without importing the full runtime.
    from extractor.native_runtime import preload_libstdcxx

    preload_libstdcxx()

    from extractor.binary_cfg import build_static_cfg
    from extractor.binary_inventory import (
        PinnedBinary,
        exact_symbol_inventory_policy,
        inventory_project,
        load_pinned_binary,
    )
    from extractor.fresh import extract_fresh_function
    from extractor.loaded_image import load_object_set, loaded_image_data

    provider = _provider(arguments.provider) if arguments.provider else None
    if provider is not None:
        if arguments.manifest is None:
            raise ValueError("provider extraction requires --manifest")
        pinned = load_pinned_binary(arguments.artifact, arguments.manifest, provider.inventory_policy())
    else:
        project = load_object_set(arguments.artifact, arguments.objects)
        policy = exact_symbol_inventory_policy(tuple(dict.fromkeys((arguments.root, *arguments.candidate_root))), open_transfers=True, discover_direct_targets=not arguments.root_only)
        manifest = inventory_project(project, arguments.artifact, policy)
        pinned = PinnedBinary(arguments.artifact, manifest, project)
    actual_cfg = build_static_cfg(pinned)
    if arguments.cfg is None:
        cfg = actual_cfg
    else:
        cfg = json.loads(arguments.cfg.read_text(encoding="utf-8"))
        if cfg != actual_cfg:
            raise ValueError("supplied CFG differs from the recomputed CFG")

    roots = tuple(cfg["roots"]) if pinned.manifest.get("open_transfers") else _root_closure(cfg, arguments.root)
    functions = tuple(
        extract_fresh_function(pinned, cfg, function_id)
        for function_id in roots
    )
    external_edges = provider.external_call_edges(pinned, cfg) if provider else ()
    result = {
        "schema": "wruh-fresh-bundle-v1",
        "image_sha256": pinned.manifest["image_sha256"],
        "root_id": arguments.root,
        "cfg": cfg,
        "functions": [function.to_data() for function in functions],
        "external_edges": [edge.to_data() for edge in external_edges],
    }

    if provider is None:
        result["loaded_image"] = loaded_image_data(pinned.project)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", type=Path)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--objects", type=Path, help="explicit object-set JSON paths and base addresses")
    parser.add_argument("--cfg", type=Path)
    parser.add_argument("--root", required=True)
    parser.add_argument("--root-only", action="store_true", help="do not recursively select direct callees; preserve their transfers as open")
    parser.add_argument("--candidate-root", action="append", default=[], help="additional discovered target to extract; unmatched transfers stay open")
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    from ayxg.codec import dumps

    arguments.output.write_text(dumps(_run(arguments), indent=2, sort_keys=True) + "\n")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
