"""Pure operations over the canonical typed expression DAG."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace

from extractor.artifact import ArtifactError, TypedExpr


def substitute_exprs(
    expressions: Sequence[TypedExpr],
    replacements: Mapping[str, TypedExpr],
) -> tuple[TypedExpr, ...]:
    """Simultaneously substitute variables across a shared expression DAG."""

    if not replacements:
        return tuple(expressions)
    memo: dict[int, tuple[TypedExpr, TypedExpr]] = {}
    for root in expressions:
        stack = [(root, False)]
        while stack:
            node, expanded = stack.pop()
            key = id(node)
            if key in memo:
                continue
            if node.op == "var" and node.name in replacements:
                result = replacements[node.name]
                if result.sort != node.sort:
                    raise ArtifactError(
                        f"replacement for {node.name!r} has the wrong sort"
                    )
                memo[key] = (node, result)
            elif expanded:
                args = tuple(memo[id(arg)][1] for arg in node.args)
                unchanged = all(
                    replacement is original
                    for replacement, original in zip(args, node.args, strict=True)
                )
                memo[key] = (node, node if unchanged else replace(node, args=args))
            else:
                stack.append((node, True))
                stack.extend(
                    (argument, False)
                    for argument in reversed(node.args)
                    if id(argument) not in memo
                )
    return tuple(memo[id(expression)][1] for expression in expressions)


def substitute_expr(
    expression: TypedExpr,
    replacements: Mapping[str, TypedExpr],
) -> TypedExpr:
    """Simultaneously substitute typed variables without changing sorts."""

    return substitute_exprs((expression,), replacements)[0]
