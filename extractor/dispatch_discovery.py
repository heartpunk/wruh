"""Loaded-image discovery hints from one straight-line jump computation.

These addresses extend decoding only. They never replace or constrain the
instruction's symbolic target, and they do not establish exhaustive coverage.
"""

from __future__ import annotations

from typing import Any


def recover_block_dispatch(
    pinned: Any, instructions: list[dict[str, Any]], *, max_entries: int = 256
) -> list[int]:
    """Compose existing instruction summaries; inspect a bounded pointer load.

    No predecessor search or cross-block iteration is performed. Unknown bases,
    modified table memory, and computations outside the budget remain open.
    """
    import z3
    from ayxg.expr import TypedExpr
    from ayxg.z3 import declaration_variables, expr_to_z3

    from extractor.amd64_state import step_instruction_outcomes
    from extractor.artifact import StaticOccurrenceId
    from extractor.fresh import _local_edges, artifact_declarations
    from extractor.fresh_composition import _apply

    declarations = artifact_declarations(pinned.project.arch)
    state = {item.name: TypedExpr.var(item.name, item.sort) for item in declarations}
    target = None
    for index, instruction in enumerate(instructions):
        family = step_instruction_outcomes(pinned.project, instruction["address"])
        # A straight-line computation must have one ordinary outcome.
        if len(family.outcomes) != 1 or family.outcomes[0].jumpkind != "Ijk_Boring":
            return []
        edge, = _local_edges(declarations, StaticOccurrenceId(index), family)
        _, state, target = _apply(edge, state, declarations)
    if target is None or target.kind != "symbolic":
        return []

    context = z3.Context()
    variables = declaration_variables(declarations, context)
    expression = z3.simplify(expr_to_z3(target.value, variables, context))
    # The existing instruction model represents a little-endian word load as
    # a concat of eight byte selects. Match that semantic expression, rather
    # than any register allocation or sequence of machine instructions.
    if not z3.is_app_of(expression, z3.Z3_OP_CONCAT) or expression.num_args() != 8:
        return []
    reads = list(reversed(expression.children()))
    if any(not z3.is_select(read) or not read.arg(0).eq(variables["mem"])
           for read in reads):
        return []
    address = reads[0].arg(1)
    if any(not z3.is_true(z3.simplify(read.arg(1) == address + offset))
           for offset, read in enumerate(reads)):
        return []

    solver = z3.Solver(ctx=context)
    solver.set(timeout=100)
    obj = pinned.project.loader.find_object_containing(instructions[0]["address"])
    targets = set()
    # A per-query timeout and entry budget bound optional discovery. Even a
    # partial enumeration supplies useful hints without asserting closure.
    for _ in range(max_entries):
        if solver.check() != z3.sat:
            break
        value = solver.model().eval(address, model_completion=True).as_long()
        solver.add(address != value)
        if not (obj.contains_addr(value) and obj.contains_addr(value + 7)):
            continue
        try:
            raw = pinned.project.loader.memory.load(value, 8)
        except KeyError:
            continue
        if len(raw) == 8:
            targets.add(int.from_bytes(raw, "little"))
    return sorted(targets)
