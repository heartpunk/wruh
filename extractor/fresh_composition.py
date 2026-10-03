"""Compose freshly extracted instruction summaries into bounded root paths."""

from __future__ import annotations

from ayxg.expr import TypedExpr

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Mapping

import z3

from extractor.artifact import LocalEdge, Target
from extractor.fresh import FreshFunction
from ayxg.z3 import declaration_variables, expr_to_z3
from ayxg.substitution import substitute_exprs


class FreshCompositionError(RuntimeError):
    """Fresh local edges do not determine a bounded closed handler path."""


@dataclass(frozen=True)
class ComposedPath:
    run_id: str
    guard: TypedExpr
    update: Mapping[str, TypedExpr]
    target: Target
    edge_ids: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class _Pending:
    function_id: str
    pc: int
    guard: TypedExpr
    state: Mapping[str, TypedExpr]
    calls: tuple[int, ...]
    edges: tuple[tuple[int, int], ...]
    steps: int


def _and(left: TypedExpr, right: TypedExpr) -> TypedExpr:
    return TypedExpr.conjoin(left, right)


def _target_value(
    target: TypedExpr,
    declarations: tuple[Any, ...],
) -> int | None:
    ctx = z3.Context()
    variables = declaration_variables(declarations, ctx)
    expression = z3.simplify(expr_to_z3(target, variables, ctx))
    if z3.is_bv_value(expression):
        return expression.as_long()
    return None


def _apply(
    edge: LocalEdge,
    state: Mapping[str, TypedExpr],
    declarations: tuple[Any, ...],
) -> tuple[TypedExpr, dict[str, TypedExpr], Target]:
    replacements = {item.name: state[item.name] for item in declarations}
    summary = edge.summary
    guard = substitute_exprs((summary.guard,), replacements)[0]
    update = {
        assignment.name: substitute_exprs((assignment.value,), replacements)[0]
        for assignment in summary.simultaneous_update
    }
    if summary.external_effect is not None:
        raise FreshCompositionError(
            f"edge at {edge.source:#x} retains an unmaterialized external effect"
        )
    if set(update) != set(replacements):
        missing = sorted(set(replacements) - set(update))
        extra = sorted(set(update) - set(replacements))
        raise FreshCompositionError(
            f"edge at {edge.source:#x} has incomplete updates: "
            f"missing={missing}, extra={extra}"
        )
    target = summary.target
    if target.kind == "symbolic":
        assert isinstance(target.value, TypedExpr)
        target = Target(
            "symbolic",
            substitute_exprs((target.value,), replacements)[0],
        )
    return guard, update, target


def compose_fresh_paths(
    cfg: Mapping[str, Any],
    functions: tuple[FreshFunction, ...],
    root_id: str,
    external_edges: tuple[LocalEdge, ...] = (),
    *,
    max_steps: int = 4096,
    max_paths: int = 4096,
) -> tuple[ComposedPath, ...]:
    """Symbolically follow only fresh local summaries and provider edges.

    Calls are followed through provider-selected roots or external edges. A
    return is routed to its statically witnessed continuation only under an
    explicit equality guard; any alternate return target remains a terminal
    path and therefore can fail the equivalence query.
    """
    if root_id not in {function.function_id for function in functions}:
        raise FreshCompositionError(f"unknown fresh root {root_id!r}")
    if max_steps <= 0 or max_paths <= 0:
        raise FreshCompositionError("path bounds must be positive")

    roots = cfg.get("roots")
    if not isinstance(roots, Mapping):
        raise FreshCompositionError("CFG has no roots")
    fresh_by_id = {function.function_id: function for function in functions}
    if len(fresh_by_id) != len(functions):
        raise FreshCompositionError("duplicate fresh function identity")
    declarations = fresh_by_id[root_id].declarations
    declaration_names = tuple(item.name for item in declarations)
    for function in functions:
        if function.declarations != declarations:
            raise FreshCompositionError("fresh roots use different declarations")

    edges_by_source: dict[int, list[LocalEdge]] = defaultdict(list)
    for function in functions:
        for edge in function.local_edges:
            edges_by_source[edge.source].append(edge)
    primitive_by_source: dict[int, list[LocalEdge]] = defaultdict(list)
    for edge in external_edges:
        primitive_by_source[edge.source].append(edge)
    for edges in (*edges_by_source.values(), *primitive_by_source.values()):
        edges.sort(key=lambda item: (item.id.occurrence.value, item.id.outcome.value))

    selected_roots = set(fresh_by_id)
    root_at = {
        value["address"]: name
        for name, value in roots.items()
        if name in selected_roots
    }
    instruction_at: dict[int, dict[str, Any]] = {}
    successors_at: dict[int, tuple[int, ...]] = {}
    call_at: dict[int, dict[str, Any]] = {}
    for function_id in selected_roots:
        root = roots[function_id]
        for block in root["blocks"]:
            for instruction in block["instructions"]:
                instruction_at[instruction["address"]] = instruction
                successors_at[instruction["address"]] = tuple(block["successors"])
        for call in root.get("calls", ()):
            call_at[call["address"]] = call

    initial = {
        name: TypedExpr.var(name, declaration.sort)
        for name, declaration in zip(declaration_names, declarations, strict=True)
    }
    queue = deque([
        _Pending(
            root_id,
            int(roots[root_id]["address"]),
            TypedExpr.bool_lit(True),
            initial,
            (),
            (),
            0,
        )
    ])
    completed: list[ComposedPath] = []

    def record(path: _Pending, state: Mapping[str, TypedExpr], target: Target) -> None:
        sequence = path.edges
        run_id = "fresh." + ".".join(
            f"{occurrence:04d}_{outcome:03d}" for occurrence, outcome in sequence
        )
        completed.append(ComposedPath(run_id, path.guard, dict(state), target, sequence))
        if len(completed) > max_paths:
            raise FreshCompositionError("fresh path count exceeded its bound")

    while queue:
        path = queue.popleft()
        if path.steps >= max_steps:
            raise FreshCompositionError(
                f"{root_id} exceeded its {max_steps}-step fresh path bound"
            )
        instruction = instruction_at.get(path.pc)
        primitive_edges = primitive_by_source.get(path.pc, ())
        if instruction is None and not primitive_edges:
            raise FreshCompositionError(
                f"fresh path reached undeclared control target {path.pc:#x}"
            )
        is_primitive = instruction is None
        if is_primitive:
            candidates = primitive_edges
        else:
            candidates = edges_by_source.get(path.pc, ())
        if not candidates:
            raise FreshCompositionError(
                f"no fresh transition at control target {path.pc:#x}"
            )

        for edge in candidates:
            edge_guard, state_after, target = _apply(edge, path.state, declarations)
            guard = _and(path.guard, edge_guard)
            edge_ids = path.edges + ((edge.id.occurrence.value, edge.id.outcome.value),)
            updated = _Pending(
                path.function_id,
                path.pc,
                guard,
                state_after,
                path.calls,
                edge_ids,
                path.steps + 1,
            )

            if is_primitive:
                if not path.calls:
                    raise FreshCompositionError("external edge has no matching call")
                continuation = path.calls[-1]
                if target.kind == "address":
                    target_value = int(target.value)
                    if target_value != continuation:
                        record(updated, state_after, target)
                        continue
                    resumed = dict(state_after)
                    resumed["rip"] = TypedExpr.bv_lit(64, continuation)
                    queue.append(replace_pending(
                        updated,
                        pc=continuation,
                        state=resumed,
                        calls=path.calls[:-1],
                    ))
                    continue
                if target.kind != "symbolic" or not isinstance(target.value, TypedExpr):
                    record(updated, state_after, target)
                    continue
                expected = TypedExpr.bv_lit(64, continuation)
                expected_guard = TypedExpr.equal(target.value, expected)
                wrong_guard = TypedExpr.not_equal(target.value, expected)
                record(
                    replace_pending(updated, guard=_and(updated.guard, wrong_guard)),
                    state_after,
                    target,
                )
                resumed = dict(state_after)
                resumed["rip"] = expected
                queue.append(replace_pending(
                    updated,
                    pc=continuation,
                    guard=_and(updated.guard, expected_guard),
                    state=resumed,
                    calls=path.calls[:-1],
                ))
                continue

            mnemonic = instruction["mnemonic"]
            if mnemonic == "ret":
                if not path.calls:
                    record(updated, state_after, target)
                    continue
                continuation = path.calls[-1]
                if target.kind == "address":
                    if int(target.value) == continuation:
                        resumed = dict(state_after)
                        resumed["rip"] = TypedExpr.bv_lit(64, continuation)
                        queue.append(replace_pending(
                            updated,
                            pc=continuation,
                            state=resumed,
                            calls=path.calls[:-1],
                        ))
                    else:
                        record(updated, state_after, target)
                    continue
                if target.kind == "symbolic" and isinstance(target.value, TypedExpr):
                    expected = TypedExpr.bv_lit(64, continuation)
                    expected_guard = TypedExpr.equal(target.value, expected)
                    wrong_guard = TypedExpr.not_equal(target.value, expected)
                    record(
                        replace_pending(updated, guard=_and(updated.guard, wrong_guard)),
                        state_after,
                        target,
                    )
                    resumed = dict(state_after)
                    resumed["rip"] = expected
                    queue.append(replace_pending(
                        updated,
                        pc=continuation,
                        guard=_and(updated.guard, expected_guard),
                        state=resumed,
                        calls=path.calls[:-1],
                    ))
                    continue
                record(updated, state_after, target)
                continue

            call = call_at.get(path.pc)
            if call is not None:
                continuation = path.pc + instruction["size"]
                if target.kind == "address":
                    address = int(target.value)
                    if address in instruction_at or address in primitive_by_source:
                        queue.append(replace_pending(updated, pc=address,
                            function_id=root_at.get(address, path.function_id),
                            calls=path.calls + (continuation,)))
                    else:
                        record(updated, state_after, target)
                    continue
                if target.kind == "symbolic" and isinstance(target.value, TypedExpr):
                    concrete = _target_value(target.value, declarations)
                    addresses = (concrete,) if concrete is not None else tuple(sorted(address for address in root_at if root_at[address] != path.function_id))
                    equalities = tuple(TypedExpr.equal(target.value,
                        TypedExpr.bv_lit(64, address)) for address in addresses)
                    record(replace_pending(updated, guard=_and(updated.guard,
                        TypedExpr.negate(TypedExpr.disjoin(*equalities)))), state_after, target)
                    for address, equality in zip(addresses, equalities, strict=True):
                        branch = replace_pending(updated, guard=_and(updated.guard, equality))
                        if address not in instruction_at and address not in primitive_by_source:
                            record(branch, state_after, target)
                        else:
                            queue.append(replace_pending(branch, pc=address,
                                function_id=root_at.get(address, path.function_id),
                                calls=path.calls + (continuation,)))
                    continue
                record(updated, state_after, target)
                continue

            if target.kind == "address":
                target_address = int(target.value)
                if target_address in instruction_at or target_address in primitive_by_source:
                    queue.append(replace_pending(
                        updated,
                        function_id=root_at.get(target_address, path.function_id),
                        pc=target_address,
                    ))
                else:
                    record(updated, state_after, target)
                continue
            if target.kind == "symbolic" and isinstance(target.value, TypedExpr):
                concrete = _target_value(target.value, declarations)
                if concrete is not None:
                    successors = (concrete,)
                else:
                    successors = successors_at.get(path.pc, ())
                if not successors:
                    successors = tuple(sorted(root_at))
                target_guards = tuple(
                    TypedExpr.equal(
                        target.value, TypedExpr.bv_lit(64, address)
                    )
                    for address in successors
                )
                residual_guard = TypedExpr.negate(
                    TypedExpr.disjoin(*target_guards)
                )
                record(
                    replace_pending(
                        updated,
                        guard=_and(updated.guard, residual_guard),
                    ),
                    state_after,
                    target,
                )
                for address, target_guard in zip(successors, target_guards, strict=True):
                    if address not in instruction_at and address not in primitive_by_source:
                        record(
                            replace_pending(
                                updated,
                                guard=_and(updated.guard, target_guard),
                            ),
                            state_after,
                            Target("address", address),
                        )
                        continue
                    resumed = dict(state_after)
                    resumed["rip"] = TypedExpr.bv_lit(64, address)
                    queue.append(replace_pending(
                        updated,
                        function_id=root_at.get(address, path.function_id),
                        pc=address,
                        guard=_and(updated.guard, target_guard),
                        state=resumed,
                    ))
                continue
            record(updated, state_after, target)

    completed.sort(key=lambda item: item.edge_ids)
    if not completed:
        raise FreshCompositionError(f"{root_id} has no complete fresh paths")
    return tuple(
        replace_path_name(path, index)
        for index, path in enumerate(completed)
    )


def replace_pending(path: _Pending, **changes: Any) -> _Pending:
    values = {
        "function_id": path.function_id,
        "pc": path.pc,
        "guard": path.guard,
        "state": path.state,
        "calls": path.calls,
        "edges": path.edges,
        "steps": path.steps,
    }
    values.update(changes)
    return _Pending(**values)


def replace_path_name(path: ComposedPath, index: int) -> ComposedPath:
    return ComposedPath(
        f"fresh.{index:04d}",
        path.guard,
        path.update,
        path.target,
        path.edge_ids,
    )
