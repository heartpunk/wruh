"""Angr operations requested by the Lean fresh-extraction driver.

One JSON line is returned for the inventory, then one for each requested
instruction. This process never assembles STS edges or a fresh artifact.
"""

from __future__ import annotations

import argparse
import json
import sys

from ayxg.codec import typed_expr_roots_dag
from ayxg.expr import TypedExpr
from ayxg.z3 import expr_from_z3, typed_conversion_cache

from extractor.amd64_state import step_instruction_outcomes
from extractor.architecture import architecture_layout
from extractor.extraction_args import add_arguments
from extractor.fresh import artifact_declarations
from extractor.linear_pipeline import prepare
from extractor.loaded_image import loaded_image_data


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    return parser.parse_args()


def _inventory(args: argparse.Namespace):
    project, records, report, image_sha256 = prepare(args)
    sites = [{"address": address, "occurrence": occurrence.to_data()} for address, occurrence in records]
    inventory = {
        "kind": "inventory", "image_sha256": image_sha256, "inventory": report,
        "declarations": [declaration.to_data() for declaration in artifact_declarations(project.arch)],
        "architecture": architecture_layout(project.arch).to_data(),
        "sites": sites,
        "loaded_image": loaded_image_data(project),
    }
    return project, inventory, {address for address, _ in records}


def _step(project, address: int) -> dict:
    family = step_instruction_outcomes(project, address)
    declarations = artifact_declarations(project.arch)
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
                "fault_kind": outcome.fault_kind,
            })
    return {
        "kind": "step", "address": address, "source_guard": source_guard,
        "expression_dag": typed_expr_roots_dag(tuple(roots)), "outcomes": outcomes,
    }


def main() -> int:
    project, inventory, sites = _inventory(_arguments())
    print(json.dumps(inventory, separators=(",", ":")), flush=True)
    for line in sys.stdin:
        request = json.loads(line)
        if request.get("op") == "quit":
            return 0
        if request.get("op") != "step" or request.get("address") not in sites:
            raise ValueError("unknown instruction request")
        print(json.dumps(_step(project, request["address"]), separators=(",", ":")), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
