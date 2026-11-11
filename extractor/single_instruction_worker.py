"""Return the existing typed AYXG encoding for one exact AMD64 instruction.

This is the angr boundary for the Lean catalogue PBT. It extracts a model from
the supplied bytes at the sampled occurrence's address; it does not generate
test state or evaluate the model.
"""
from __future__ import annotations

import argparse
import json
import sys

from ayxg.codec import typed_expr_roots_dag
from ayxg.expr import TypedExpr
from ayxg.z3 import expr_from_z3, typed_conversion_cache
from archinfo import ArchAMD64
import angr

from extractor.amd64_state import step_instruction_outcomes
from extractor.fresh import artifact_declarations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bytes", required=True, help="exact instruction bytes as hex")
    parser.add_argument("--address", required=True, type=lambda value: int(value, 0))
    args = parser.parse_args()
    encoded = bytes.fromhex(args.bytes)
    if not encoded or len(encoded) > 15:
        raise ValueError("expected one x86 instruction of 1 to 15 bytes")

    project = angr.load_shellcode(encoded, arch=ArchAMD64(), load_address=args.address)
    family = step_instruction_outcomes(project, args.address)
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
                if value is None:
                    updates.append(len(roots))
                    roots.append(TypedExpr.var(declaration.name, declaration.sort))
                else:
                    updates.append(add(value))
            target = add(outcome.target)
            outcomes.append({
                "outcome_id": outcome.outcome_id,
                "guard": guard,
                "updates": updates,
                "target": target,
                "target_value": outcome.target_value,
                "jumpkind": outcome.jumpkind,
            })

    print(json.dumps({
        "kind": "single-instruction-model",
        "address": args.address,
        "declarations": [item.to_data() for item in declarations],
        "step": {
            "kind": "step",
            "address": args.address,
            "source_guard": source_guard,
            "expression_dag": typed_expr_roots_dag(tuple(roots)),
            "outcomes": outcomes,
        },
    }, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
