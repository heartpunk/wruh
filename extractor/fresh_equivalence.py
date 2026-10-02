"""Run one ABI-provider's fresh-only opcode-handler equivalence check."""

from __future__ import annotations

from ayxg.expr import variable_sorts

from extractor.runtime_trace import start_runtime_trace

start_runtime_trace()

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

from extractor.native_runtime import preload_libstdcxx

_LIBSTDCXX = preload_libstdcxx()

import z3  # noqa: E402

from extractor.binary_cfg import build_static_cfg
from extractor.binary_inventory import load_pinned_binary
from extractor.fresh import extract_fresh_function
from extractor.fresh_composition import compose_fresh_paths
from extractor.handler_equivalence import HandlerEquivalenceBuilder
from extractor.typed_z3 import expr_to_z3, sort_to_z3


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
    provider = _provider(arguments.provider)
    policy = provider.inventory_policy()
    pinned = load_pinned_binary(arguments.artifact, arguments.manifest, policy)
    actual_cfg = build_static_cfg(pinned)
    if arguments.cfg is None:
        cfg = actual_cfg
    else:
        cfg = json.loads(arguments.cfg.read_text(encoding="utf-8"))
        if cfg != actual_cfg:
            raise ValueError("supplied CFG differs from the recomputed CFG")

    roots = _root_closure(cfg, arguments.handler)
    functions = tuple(
        extract_fresh_function(pinned, cfg, function_id)
        for function_id in roots
    )
    external_edges = provider.external_call_edges(pinned, cfg)
    contract = provider.handler_contract(arguments.handler, cfg)
    if contract.root_id != arguments.handler:
        raise ValueError("provider returned a contract for a different root")
    paths = compose_fresh_paths(
        cfg,
        functions,
        arguments.handler,
        external_edges,
        max_steps=arguments.max_steps,
        max_paths=arguments.max_paths,
    )
    builder = HandlerEquivalenceBuilder(contract, paths)
    ctx = z3.Context()
    variables = {
        name: z3.Const(name, sort_to_z3(sort, ctx))
        for name, sort in variable_sorts(builder.variables).items()
    }
    memo: dict = {}
    records = []
    for query in builder.queries(selected_component=arguments.component):
        solver = z3.Solver(ctx=ctx)
        solver.set(timeout=arguments.timeout_ms)
        solver.add(expr_to_z3(query.proposition, variables, ctx, memo=memo))
        result = solver.check()
        record: dict[str, Any] = {"query": query.name, "result": str(result)}
        if result == z3.sat:
            record["counterexample"] = str(solver.model())
        elif result == z3.unknown:
            record["reason"] = solver.reason_unknown()
        records.append(record)
        print(f"{query.name}: {result}", flush=True)
    passed = bool(records) and all(item["result"] == "unsat" for item in records)
    complete = all(item["result"] != "unknown" for item in records)
    status = "PASS" if passed else "FAIL" if complete else "INCOMPLETE"
    return {
        "schema": "wruh-fresh-handler-equivalence-v1",
        "provider": provider.provider_id,
        "handler": arguments.handler,
        "image_sha256": pinned.manifest["image_sha256"],
        "fresh_roots": list(roots),
        "fresh_paths": len(paths),
        "fresh_path_edges": {
            path.run_id: [list(edge) for edge in path.edge_ids]
            for path in paths
        },
        "status": status,
        "queries": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--cfg", type=Path)
    parser.add_argument("--handler", required=True)
    parser.add_argument("--component")
    parser.add_argument("--timeout-ms", type=int, default=1_800_000)
    parser.add_argument("--max-steps", type=int, default=4096)
    parser.add_argument("--max-paths", type=int, default=4096)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--record-only", action="store_true")
    arguments = parser.parse_args()
    if arguments.timeout_ms <= 0:
        parser.error("--timeout-ms must be positive")
    result = _run(arguments)
    arguments.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"{result['handler']} fresh equivalence: {result['status']}", flush=True)
    return 0 if arguments.record_only or result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
