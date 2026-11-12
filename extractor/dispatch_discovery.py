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

    from extractor.amd64_state import Amd64AdapterError, step_instruction_outcomes
    from extractor.artifact import StaticOccurrenceId
    from extractor.fresh import _local_edges, artifact_declarations
    from extractor.fresh_composition import _apply

    declarations = artifact_declarations(pinned.project.arch)
    state = {item.name: TypedExpr.var(item.name, item.sort) for item in declarations}
    target = None
    for index, instruction in enumerate(instructions):
        try:
            family = step_instruction_outcomes(pinned.project, instruction["address"])
        except Amd64AdapterError:
            return []
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
    # Reject unknown table bases before enumerating. Candidate reads must be
    # wholly within this loaded object; a free base register cannot establish
    # that, even when an index happens to be small.
    solver.push()
    solver.add(z3.Or(z3.ULT(address, obj.min_addr),
                     z3.UGT(address, obj.max_addr - 7)))
    within_object = solver.check() == z3.unsat
    solver.pop()
    if not within_object:
        return []
    addresses = []
    # Bound the address computation before reading memory. An unconstrained
    # register must not turn into a sample of arbitrary loaded pointers.
    for _ in range(max_entries):
        result = solver.check()
        if result == z3.unsat:
            break
        if result != z3.sat:
            return []
        value = solver.model().eval(address, model_completion=True).as_long()
        solver.add(address != value)
        addresses.append(value)
    else:
        if solver.check() != z3.unsat:
            return []
    targets = set()
    for value in addresses:
        if not (obj.contains_addr(value) and obj.contains_addr(value + 7)):
            continue
        try:
            raw = pinned.project.loader.memory.load(value, 8)
        except KeyError:
            continue
        if len(raw) == 8:
            targets.add(int.from_bytes(raw, "little"))
    return sorted(targets)
