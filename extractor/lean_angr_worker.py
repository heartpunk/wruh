"""Angr operations requested by the Lean fresh-extraction driver.

One JSON line is returned for the inventory, then one for each requested
instruction. This process never assembles STS edges or a fresh artifact.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from ayxg.codec import typed_expr_roots_dag
from ayxg.expr import TypedExpr
from ayxg.z3 import expr_from_z3, typed_conversion_cache

from extractor.amd64_state import step_instruction_outcomes
from extractor.architecture import architecture_layout
from extractor.artifact import DecodedInstructionEvidence, Occurrence
from extractor.binary_cfg import build_static_cfg
from extractor.binary_inventory import (
    PinnedBinary,
    exact_symbol_inventory_policy,
    inventory_project,
    load_pinned_binary,
)
from extractor.extract_cli import _provider, _root_closure
from extractor.fresh import (
    _decoded_owners,
    _instruction_records,
    artifact_declarations,
    occurrence_catalog,
)
from extractor.loaded_image import load_object_set, loaded_image_data


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", type=Path)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--objects", type=Path)
    parser.add_argument("--cfg", type=Path)
    parser.add_argument("--root", required=True)
    parser.add_argument("--root-only", action="store_true")
    parser.add_argument("--candidate-root", action="append", default=[])
    return parser.parse_args()


def _inventory(args: argparse.Namespace):
    provider = _provider(args.provider) if args.provider else None
    if provider is not None:
        if args.manifest is None:
            raise ValueError("provider extraction requires --manifest")
        pinned = load_pinned_binary(args.artifact, args.manifest, provider.inventory_policy())
    else:
        project = load_object_set(args.artifact, args.objects)
        policy = exact_symbol_inventory_policy(
            tuple(dict.fromkeys((args.root, *args.candidate_root))),
            open_transfers=True,
            discover_direct_targets=not args.root_only,
        )
        pinned = PinnedBinary(args.artifact, inventory_project(project, args.artifact, policy), project)
    actual_cfg = build_static_cfg(pinned)
    cfg = actual_cfg if args.cfg is None else json.loads(args.cfg.read_text(encoding="utf-8"))
    if cfg != actual_cfg:
        raise ValueError("supplied CFG differs from the recomputed CFG")
    roots = tuple(cfg["roots"]) if pinned.manifest.get("open_transfers") else _root_closure(cfg, args.root)
    owners = _decoded_owners(cfg)
    catalog = occurrence_catalog(pinned, cfg)
    functions = []
    sites = set()
    for function_id in roots:
        root = cfg["roots"][function_id]
        instructions = []
        for instruction in _instruction_records(root):
            address = instruction["address"]
            sites.add(address)
            occurrence = Occurrence(
                catalog[address],
                DecodedInstructionEvidence(
                    image_sha256=root.get("image_sha256", cfg["image_sha256"]),
                    canonical_address=address,
                    instruction_bytes=instruction["bytes"],
                    architecture="AMD64",
                    decode_mode="long64",
                    instruction_identity=(f"{instruction['mnemonic']} {instruction['op_str']}").strip(),
                    function_owners=owners[address],
                ),
            )
            instructions.append({"address": address, "occurrence": occurrence.to_data()})
        functions.append({"function_id": function_id, "entry": root["address"], "sites": instructions})
    inventory = {
        "kind": "inventory",
        "image_sha256": pinned.manifest["image_sha256"],
        "root_id": args.root,
        "cfg": cfg,
        "declarations": [declaration.to_data() for declaration in artifact_declarations(pinned.project.arch)],
        "architecture": architecture_layout(pinned.project.arch).to_data(),
        "functions": functions,
        "external_edges": [edge.to_data() for edge in provider.external_call_edges(pinned, cfg)] if provider else [],
    }
    if provider is None:
        inventory["loaded_image"] = loaded_image_data(pinned.project)
    return pinned, inventory, sites


def _step(pinned: PinnedBinary, address: int) -> dict:
    family = step_instruction_outcomes(pinned.project, address)
    declarations = artifact_declarations(pinned.project.arch)
    roots: list[TypedExpr] = []

    def add(expression) -> int:
        index = len(roots)
        roots.append(expr_from_z3(expression))
        return index

    with typed_conversion_cache():
        source_guard = add(family.source_guard)
        outcomes = []
        for outcome in family.outcomes:
            guard = add(outcome.guard)
            updates = []
            for declaration in declarations:
                value = outcome.updates.get(declaration.name)
                index = add(value) if value is not None else len(roots)
                if value is None:
                    roots.append(TypedExpr.var(declaration.name, declaration.sort))
                updates.append(index)
            target = add(outcome.target)
            outcomes.append({
                "outcome_id": outcome.outcome_id,
                "guard": guard,
                "updates": updates,
                "target": target,
                "target_value": outcome.target_value,
                "jumpkind": outcome.jumpkind,
            })
    return {
        "kind": "step", "address": address, "source_guard": source_guard,
        "expression_dag": typed_expr_roots_dag(tuple(roots)), "outcomes": outcomes,
    }


def main() -> int:
    pinned, inventory, sites = _inventory(_arguments())
    print(json.dumps(inventory, separators=(",", ":")), flush=True)
    for line in sys.stdin:
        request = json.loads(line)
        if request.get("op") == "quit":
            return 0
        if request.get("op") != "step" or request.get("address") not in sites:
            raise ValueError("unknown instruction request")
        print(json.dumps(_step(pinned, request["address"]), separators=(",", ":")), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
