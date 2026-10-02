"""Provider-driven typed counterexample queries for fresh handler paths."""

from __future__ import annotations

from ayxg.expr import TypedExpr, variable_sorts

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from extractor.abi_provider import HandlerContract, SourceEdge
from extractor.fresh_composition import ComposedPath
from ayxg.substitution import substitute_exprs


@dataclass(frozen=True)
class CounterexampleQuery:
    name: str
    proposition: TypedExpr


def _namespace(
    expressions: Sequence[TypedExpr], prefix: str
) -> tuple[tuple[TypedExpr, ...], dict[str, TypedExpr]]:
    replacements = {
        name: TypedExpr.var(f"{prefix}_{name}", sort)
        for name, sort in variable_sorts(expressions).items()
    }
    return substitute_exprs(expressions, replacements), replacements


class HandlerEquivalenceBuilder:
    """Build coverage and successor counterexample queries from a provider."""

    def __init__(
        self,
        contract: HandlerContract,
        machine_paths: Sequence[ComposedPath],
    ) -> None:
        self.contract = contract
        source_roots = tuple(
            expression
            for edge in contract.source_edges
            for expression in (edge.guard, *edge.update.values())
        )
        source_roots, self.source_variables = _namespace(source_roots, "source")
        source_iter = iter(source_roots)
        self.source_edges = tuple(
            SourceEdge(
                edge.name,
                next(source_iter),
                {name: next(source_iter) for name in edge.update},
                edge.status,
            )
            for edge in contract.source_edges
        )
        machine_roots = tuple(
            expression
            for path in machine_paths
            for expression in (path.guard, *path.update.values())
        )
        machine_roots, self.machine_variables = _namespace(
            machine_roots, "machine"
        )
        machine_iter = iter(machine_roots)
        self.machine_paths = tuple(
            ComposedPath(
                path.run_id,
                next(machine_iter),
                {name: next(machine_iter) for name in path.update},
                path.target,
                path.edge_ids,
            )
            for path in machine_paths
        )
        self.variables = tuple(
            (*self.source_variables.values(), *self.machine_variables.values())
        )
        self.abi_relation = contract.abi_relation
        self.components = tuple(item.name for item in contract.projections)
        if len(set(self.components)) != len(self.components):
            raise ValueError("provider output projection names are duplicated")

    def _differences(
        self, edge: SourceEdge, path: ComposedPath
    ) -> dict[str, TypedExpr]:
        result = {}
        for projection in self.contract.projections:
            source_value = (
                TypedExpr.bv_lit(8, edge.status)
                if projection.source_value is None
                else substitute_exprs(
                    (projection.source_value,), edge.update
                )[0]
            )
            machine_value = substitute_exprs(
                (projection.machine_value,), path.update
            )[0]
            if source_value.sort != machine_value.sort:
                raise ValueError(
                    f"projection {projection.name!r} has mismatched sorts"
                )
            result[projection.name] = TypedExpr.not_equal(
                source_value, machine_value
            )
        return result

    def queries(
        self,
        *,
        selected_component: str | None = None,
    ) -> Iterable[CounterexampleQuery]:
        if selected_component is not None and selected_component not in self.components:
            raise ValueError(f"unknown observation component {selected_component!r}")
        yield CounterexampleQuery(
            f"{self.contract.root_id} guard coverage",
            TypedExpr.conjoin(
                self.abi_relation,
                TypedExpr.not_equal(
                    TypedExpr.disjoin(*(edge.guard for edge in self.source_edges)),
                    TypedExpr.disjoin(*(path.guard for path in self.machine_paths)),
                ),
            ),
        )
        for edge in self.source_edges:
            for path in self.machine_paths:
                differences = self._differences(edge, path)
                components = (
                    (selected_component,)
                    if selected_component is not None
                    else self.components
                )
                suffix = f" {selected_component}" if selected_component else ""
                yield CounterexampleQuery(
                    f"{self.contract.root_id} {edge.name} {path.run_id}{suffix} successor",
                    TypedExpr.conjoin(
                        self.abi_relation,
                        edge.guard,
                        path.guard,
                        TypedExpr.disjoin(*(differences[name] for name in components)),
                    ),
                )
