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
    infeasible loaded-image values, and computations outside the budget remain open.
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
    # Collect the loaded bytes without descending into their addresses (which
    # may themselves depend on an input-memory index). Recognize the target
    # algebraically, so Z3's expansion of SignExt into concat/extract is harmless.
    reads_by_id = {}
    def collect(node):
        if z3.is_select(node):
            reads_by_id[node.get_id()] = node
            return
        for child in node.children():
            collect(child)
    collect(expression)
    reads = list(reads_by_id.values())
    width = len(reads)
    if width not in (4, 8):
        return []
    memory = reads[0].arg(0)
    if any(not read.arg(0).eq(memory) for read in reads):
        return []
    if width == 8 and not memory.eq(variables["mem"]):
        return []  # Preserve the absolute-pointer recovery contract.
    original = memory
    while z3.is_store(original):
        original = original.arg(0)
    if not original.eq(variables["mem"]):
        return []
    # Find the low byte by proving that every other byte is at a consecutive
    # address. Do not depend on expression traversal order.
    for first in reads:
        ordered = []
        for offset in range(width):
            matches = [read for read in reads if z3.is_true(z3.simplify(
                read.arg(1) == first.arg(1) + offset))]
            if len(matches) != 1:
                break
            ordered.append(matches[0])
        if len(ordered) == width:
            reads = ordered
            break
    else:
        return []
    address = reads[0].arg(1)
    word = z3.FreshConst(z3.BitVecSort(width * 8, ctx=context), "dispatch_word")
    computed = z3.simplify(z3.substitute(expression, *[
        (read, z3.Extract(8 * index + 7, 8 * index, word))
        for index, read in enumerate(reads)
    ]))
    base = z3.simplify(z3.substitute(computed, (word, z3.BitVecVal(0, width * 8, ctx=context))))
    if not z3.is_bv_value(base):
        return []
    expected = word if width == 8 else base + z3.SignExt(32, word)
    # Absolute pointers retain their existing shape; relative entries require
    # a concrete additive base and signed 32-bit displacement.
    if not z3.is_true(z3.simplify(computed == expected)):
        return []

    # Enumerate an overapproximation of the address's input reads. Their
    # values are unconstrained already; fresh bytes avoid making the solver
    # analyze prologue Store chains merely to establish a masked index bound.
    # The original address and memory remain intact in the witness query.
    inputs = {}
    def collect_inputs(node):
        if z3.is_select(node):
            inputs[node.get_id()] = node
            return
        for child in node.children():
            collect_inputs(child)
    collect_inputs(address)
    enumeration_address = z3.simplify(z3.substitute(address, *[
        (read, z3.FreshConst(read.sort(), "dispatch_index"))
        for read in inputs.values()
    ]))

    solver = z3.Solver(ctx=context)
    solver.set(timeout=100)
    obj = pinned.project.loader.find_object_containing(instructions[0]["address"])
    # Reject unknown table bases before enumerating. Candidate reads must be
    # wholly within this loaded object; a free base register cannot establish
    # that, even when an index happens to be small.
    solver.push()
    solver.add(z3.Or(z3.ULT(enumeration_address, obj.min_addr),
                     z3.UGT(enumeration_address, obj.max_addr - (width - 1))))
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
        value = solver.model().eval(enumeration_address, model_completion=True).as_long()
        solver.add(enumeration_address != value)
        addresses.append(value)
    else:
        if solver.check() != z3.unsat:
            return []
    targets = set()
    for value in addresses:
        if not (obj.contains_addr(value) and obj.contains_addr(value + width - 1)):
            continue
        try:
            raw = pinned.project.loader.memory.load(value, width)
        except KeyError:
            continue
        if len(raw) == width:
            loaded = int.from_bytes(raw, "little", signed=width == 4)
            candidate = (loaded + (base.as_long() if width == 4 else 0)) % (1 << 64)
            if width == 4:
                # Prologue stores may alias the table: do not erase them or
                # assume a disjoint stack. Require a witness of this exact
                # target under the original loaded-image bytes. This query is
                # local to discovery; no assumptions escape into the artifact.
                witness = z3.Solver(ctx=context)
                witness.set(timeout=100)
                witness.add(address == value, expression == candidate)
                witness.add(*[variables["mem"][value + offset] == byte
                              for offset, byte in enumerate(raw)])
                if witness.check() != z3.sat:
                    continue
            targets.add(candidate)
    return sorted(targets)
