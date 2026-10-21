"""Architecture-specific step construction from Z3 state expressions."""
from __future__ import annotations
from collections.abc import Mapping
from extractor.native_runtime import preload_libstdcxx
_LIBSTDCXX = preload_libstdcxx()
import z3
from ayxg.expr import BOOL, ArtifactError, Declaration, TypedExpr
from ayxg.z3 import expr_from_z3
from extractor.artifact import Assignment, StepSummary, Target, BV64

def complete_update(
    declarations: tuple[Declaration, ...],
    updates: Mapping[str, z3.ExprRef],
) -> tuple[Assignment, ...]:
    declared = {declaration.name: declaration for declaration in declarations}
    unknown = set(updates) - set(declared)
    if unknown:
        raise ArtifactError(
            f"update names are not declared: {sorted(unknown)}"
        )
    result = []
    for declaration in declarations:
        value = (
            expr_from_z3(updates[declaration.name])
            if declaration.name in updates
            else TypedExpr.var(declaration.name, declaration.sort)
        )
        if value.sort != declaration.sort:
            raise ArtifactError(
                f"update for {declaration.name!r} has wrong sort"
            )
        result.append(Assignment(declaration.name, value))
    return tuple(result)


def step_summary_from_z3(
    declarations: tuple[Declaration, ...],
    *,
    guard: z3.BoolRef,
    updates: Mapping[str, z3.ExprRef],
    target: int | z3.BitVecRef | str,
    mirrored_pc: z3.BitVecRef,
) -> StepSummary:
    typed_guard = expr_from_z3(guard)
    typed_pc = expr_from_z3(mirrored_pc)
    if typed_guard.sort != BOOL:
        raise ArtifactError("step guard is not Bool")
    if typed_pc.sort != BV64:
        raise ArtifactError("mirrored PC is not BV64")
    if type(target) is int:
        typed_target = Target("address", target)
    elif isinstance(target, z3.ExprRef):
        typed_target = Target("symbolic", expr_from_z3(target))
    elif target in {"halt", "error", "stuck"}:
        typed_target = Target(target)
    else:
        raise ArtifactError("target is neither address, BV64, nor terminal")
    result = StepSummary(
        guard=typed_guard,
        simultaneous_update=complete_update(declarations, updates),
        target=typed_target,
        mirrored_pc=typed_pc,
    )
    result.validate(declarations)
    return result
