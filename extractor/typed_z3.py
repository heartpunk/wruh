"""Fail-closed Z3 adapter for the bounded typed extraction artifact surface."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from threading import local
from typing import Iterator
from extractor.native_runtime import preload_libstdcxx

_LIBSTDCXX = preload_libstdcxx()

import z3  # noqa: E402

from extractor.artifact import (
    BOOL,
    BV64,
    Assignment,
    ArtifactError,
    Declaration,
    StepSummary,
    Target,
    TermSort,
    TypedExpr,
)
from extractor.typed_expr import substitute_expr as substitute_expr  # noqa: E402


_BINARY = {
    z3.Z3_OP_BADD: "bv_add",
    z3.Z3_OP_BSUB: "bv_sub",
    z3.Z3_OP_BMUL: "bv_mul",
    z3.Z3_OP_BUDIV: "bv_udiv",
    z3.Z3_OP_BUREM: "bv_urem",
    z3.Z3_OP_BAND: "bv_and",
    z3.Z3_OP_BOR: "bv_or",
    z3.Z3_OP_BXOR: "bv_xor",
    z3.Z3_OP_BSHL: "bv_shl",
    z3.Z3_OP_BLSHR: "bv_lshr",
    z3.Z3_OP_BASHR: "bv_ashr",
    z3.Z3_OP_ULT: "bv_ult",
    z3.Z3_OP_ULEQ: "bv_ule",
    z3.Z3_OP_SLT: "bv_slt",
    z3.Z3_OP_SLEQ: "bv_sle",
    z3.Z3_OP_EQ: "eq",
}

_REVERSED_BINARY = {
    z3.Z3_OP_UGEQ: "bv_ule",
}

_ASSOCIATIVE_BV = {
    z3.Z3_OP_BADD,
    z3.Z3_OP_BMUL,
    z3.Z3_OP_BAND,
    z3.Z3_OP_BOR,
    z3.Z3_OP_BXOR,
}

_CONVERSION_LOCAL = local()


@contextmanager
def typed_conversion_cache() -> Iterator[None]:
    """Share pure Z3-node translations across one complete artifact object."""

    existing = getattr(_CONVERSION_LOCAL, "cache", None)
    if existing is not None:
        yield
        return
    _CONVERSION_LOCAL.cache = {}
    try:
        yield
    finally:
        del _CONVERSION_LOCAL.cache


def sort_from_z3(sort: z3.SortRef) -> TermSort:
    if sort.kind() == z3.Z3_BOOL_SORT:
        return BOOL
    if sort.kind() == z3.Z3_BV_SORT:
        return TermSort.bv(sort.size())
    if sort.kind() == z3.Z3_ARRAY_SORT:
        domain = sort.domain()
        range_sort = sort.range()
        if (
            domain.kind() != z3.Z3_BV_SORT
            or range_sort.kind() != z3.Z3_BV_SORT
        ):
            raise ArtifactError("only BV-indexed BV-valued arrays are admitted")
        return TermSort.array(domain.size(), range_sort.size())
    raise ArtifactError(f"unsupported Z3 sort: {sort}")


def sort_to_z3(sort: TermSort, ctx: z3.Context) -> z3.SortRef:
    """Reconstruct one admitted artifact sort in the supplied context."""

    if sort == BOOL:
        return z3.BoolSort(ctx=ctx)
    if sort.kind == "bv":
        return z3.BitVecSort(sort.width, ctx=ctx)
    if sort.kind == "array":
        return z3.ArraySort(
            z3.BitVecSort(sort.index_width, ctx=ctx),
            z3.BitVecSort(sort.value_width, ctx=ctx),
        )
    raise ArtifactError(f"unsupported artifact sort: {sort.kind!r}")


def declaration_variables(
    declarations: tuple[Declaration, ...],
    ctx: z3.Context,
) -> dict[str, z3.ExprRef]:
    """Create one shared Z3 variable environment for semantic comparison."""

    result: dict[str, z3.ExprRef] = {}
    for declaration in declarations:
        sort = sort_to_z3(declaration.sort, ctx)
        result[declaration.name] = z3.Const(declaration.name, sort)
    return result


def expr_to_z3(
    expression: TypedExpr,
    variables: Mapping[str, z3.ExprRef],
    ctx: z3.Context,
    *,
    memo: dict[int, tuple[TypedExpr, z3.ExprRef]] | None = None,
) -> z3.ExprRef:
    """Interpret one typed expression in a fixed Z3 environment."""

    conversion_memo = {} if memo is None else memo
    stack = [(expression, False)]
    while stack:
        node, expanded = stack.pop()
        key = id(node)
        if key in conversion_memo:
            continue
        if node.op == "var":
            result = variables.get(node.name)
            if result is None:
                raise ArtifactError(
                    f"expression variable {node.name!r} is not declared"
                )
            if sort_from_z3(result.sort()) != node.sort:
                raise ArtifactError(
                    f"expression variable {node.name!r} has the wrong sort"
                )
        elif node.op == "bool_lit":
            result = z3.BoolVal(node.value, ctx=ctx)
        elif node.op == "bv_lit":
            result = z3.BitVecVal(node.value, node.sort.width, ctx=ctx)
        elif not expanded:
            stack.append((node, True))
            stack.extend(
                (argument, False)
                for argument in reversed(node.args)
                if id(argument) not in conversion_memo
            )
            continue
        else:
            args = tuple(conversion_memo[id(arg)][1] for arg in node.args)
            if node.op == "const_array":
                result = z3.K(sort_to_z3(node.sort, ctx).domain(), args[0])
            elif node.op == "bool_not":
                result = z3.Not(args[0])
            elif node.op == "bv_not":
                result = ~args[0]
            elif node.op == "bool_and":
                result = z3.And(args[0], args[1])
            elif node.op == "bool_or":
                result = z3.Or(args[0], args[1])
            elif node.op == "bv_add":
                result = args[0] + args[1]
            elif node.op == "bv_sub":
                result = args[0] - args[1]
            elif node.op == "bv_mul":
                result = args[0] * args[1]
            elif node.op == "bv_udiv":
                result = z3.UDiv(args[0], args[1])
            elif node.op == "bv_urem":
                result = z3.URem(args[0], args[1])
            elif node.op == "bv_and":
                result = args[0] & args[1]
            elif node.op == "bv_or":
                result = args[0] | args[1]
            elif node.op == "bv_xor":
                result = args[0] ^ args[1]
            elif node.op == "bv_shl":
                result = args[0] << args[1]
            elif node.op == "bv_lshr":
                result = z3.LShR(args[0], args[1])
            elif node.op == "bv_ashr":
                result = args[0] >> args[1]
            elif node.op == "bv_ult":
                result = z3.ULT(args[0], args[1])
            elif node.op == "bv_ule":
                result = z3.ULE(args[0], args[1])
            elif node.op == "bv_slt":
                result = args[0] < args[1]
            elif node.op == "bv_sle":
                result = args[0] <= args[1]
            elif node.op == "eq":
                result = args[0] == args[1]
            elif node.op == "ite":
                result = z3.If(args[0], args[1], args[2])
            elif node.op == "zero_extend":
                result = z3.ZeroExt(node.amount, args[0])
            elif node.op == "sign_extend":
                result = z3.SignExt(node.amount, args[0])
            elif node.op == "extract":
                result = z3.Extract(node.hi, node.lo, args[0])
            elif node.op == "concat":
                result = z3.Concat(args[0], args[1])
            elif node.op == "select":
                result = z3.Select(args[0], args[1])
            elif node.op == "store":
                result = z3.Store(args[0], args[1], args[2])
            else:
                raise ArtifactError(
                    f"unsupported typed expression operator: {node.op!r}"
                )
        conversion_memo[key] = (node, result)
    return conversion_memo[id(expression)][1]


def _fold(op: str, args: tuple[TypedExpr, ...], identity: bool) -> TypedExpr:
    if not args:
        return TypedExpr.bool_lit(identity)
    result = args[0]
    for arg in args[1:]:
        result = TypedExpr.binary(op, result, arg)
    return result


def expr_from_z3(expression: z3.ExprRef) -> TypedExpr:
    """Translate exactly the admitted ordinary QF_ABV surface."""

    cache = getattr(_CONVERSION_LOCAL, "cache", None)
    if cache is None:
        with typed_conversion_cache():
            return expr_from_z3(expression)
    key = (expression.ctx_ref().value, expression.get_id())
    cached = cache.get(key)
    if cached is not None:
        return cached[1]
    result = _expr_from_z3_uncached(expression)
    cache[key] = (expression, result)
    return result


def _expr_from_z3_uncached(expression: z3.ExprRef) -> TypedExpr:
    """Translate one node while `expr_from_z3` owns DAG memoization."""

    if not isinstance(expression, z3.ExprRef):
        raise ArtifactError("typed Z3 input must be an expression")
    sort = sort_from_z3(expression.sort())
    if z3.is_true(expression):
        return TypedExpr.bool_lit(True)
    if z3.is_false(expression):
        return TypedExpr.bool_lit(False)
    if z3.is_bv_value(expression):
        return TypedExpr.bv_lit(expression.size(), expression.as_long())

    kind = expression.decl().kind()
    raw_children = tuple(expression.children())
    if kind in {z3.Z3_OP_AND, z3.Z3_OP_OR}:
        raw_children = tuple(sorted(raw_children, key=lambda child: child.sexpr()))
    children = tuple(expr_from_z3(child) for child in raw_children)
    if kind == z3.Z3_OP_UNINTERPRETED and not children:
        return TypedExpr.var(str(expression.decl().name()), sort)
    if kind == z3.Z3_OP_NOT:
        return TypedExpr.unary("bool_not", children[0])
    if kind == z3.Z3_OP_AND:
        return _fold("bool_and", children, True)
    if kind == z3.Z3_OP_OR:
        return _fold("bool_or", children, False)
    if kind == z3.Z3_OP_ITE:
        return TypedExpr.ite(children[0], children[1], children[2])
    if kind in _BINARY:
        if kind == z3.Z3_OP_EQ and len(children) >= 2:
            return _fold(
                "bool_and",
                tuple(
                    TypedExpr.binary("eq", children[0], child)
                    for child in children[1:]
                ),
                True,
            )
        if kind in _ASSOCIATIVE_BV and len(children) >= 2:
            result = children[0]
            for child in children[1:]:
                result = TypedExpr.binary(_BINARY[kind], result, child)
            return result
        if len(children) != 2:
            raise ArtifactError(
                f"Z3 operator {expression.decl().name()} ({kind}) has "
                f"arity {len(children)}; expected 2"
            )
        return TypedExpr.binary(_BINARY[kind], children[0], children[1])
    if kind in _REVERSED_BINARY:
        if len(children) != 2:
            raise ArtifactError(
                f"Z3 operator {expression.decl().name()} ({kind}) has "
                f"arity {len(children)}; expected 2"
            )
        return TypedExpr.binary(
            _REVERSED_BINARY[kind],
            children[1],
            children[0],
        )
    if kind == z3.Z3_OP_DISTINCT:
        if len(children) != 2:
            raise ArtifactError("only binary distinct is admitted")
        return TypedExpr.unary(
            "bool_not",
            TypedExpr.binary("eq", children[0], children[1]),
        )
    if kind == z3.Z3_OP_BNOT:
        return TypedExpr.unary("bv_not", children[0])
    if kind in {z3.Z3_OP_ZERO_EXT, z3.Z3_OP_SIGN_EXT}:
        params = expression.params()
        if len(params) != 1 or type(params[0]) is not int:
            raise ArtifactError("Z3 extension has malformed parameters")
        return TypedExpr(
            "zero_extend" if kind == z3.Z3_OP_ZERO_EXT else "sign_extend",
            sort,
            children,
            amount=params[0],
        )
    if kind == z3.Z3_OP_EXTRACT:
        params = expression.params()
        if (
            len(params) != 2
            or type(params[0]) is not int
            or type(params[1]) is not int
        ):
            raise ArtifactError("Z3 extract has malformed parameters")
        return TypedExpr(
            "extract",
            sort,
            children,
            hi=params[0],
            lo=params[1],
        )
    if kind == z3.Z3_OP_CONCAT:
        if len(children) < 2:
            raise ArtifactError("Z3 concat must have at least two operands")
        result = children[0]
        for child in children[1:]:
            result = TypedExpr(
                "concat",
                TermSort.bv(result.sort.width + child.sort.width),
                (result, child),
            )
        return result
    if kind == z3.Z3_OP_CONST_ARRAY:
        return TypedExpr("const_array", sort, children)
    if kind == z3.Z3_OP_SELECT:
        return TypedExpr("select", sort, children)
    if kind == z3.Z3_OP_STORE:
        return TypedExpr("store", sort, children)
    raise ArtifactError(
        f"unsupported Z3 operator {expression.decl().name()} ({kind})"
    )


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
