"""Canonical AMD64 symbolic state adapted from the mxoq extractor."""

from __future__ import annotations

import importlib
import logging
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from typing import Any

from extractor import runtime
from extractor.amd64_terminals import is_ud2_instruction
from extractor.architecture import NORMALIZED_AMD64_FLAGS, architecture_layout

archinfo = importlib.import_module("archinfo")
z3 = importlib.import_module("z3")


class Amd64AdapterError(RuntimeError):
    """The exact instruction does not satisfy the E5 adapter contract."""


FLAG_NAMES = ("CF", "ZF", "SF", "OF", "PF", "AF")
MEMORY_NAME = "mem"
# Derived from the actual installed engine metadata; project-specific extraction
# obtains the layout from project.arch and checks this declaration domain.
AMD64_LAYOUT = architecture_layout(archinfo.ArchAMD64())
REGISTER_NAMES = tuple(s.name for s in AMD64_LAYOUT.storage
                       if s.name not in NORMALIZED_AMD64_FLAGS)
CANONICAL_NAMES = REGISTER_NAMES + tuple(f"rflags_{n}" for n in FLAG_NAMES) + (MEMORY_NAME,)

LTS_EXTRACTION_CONTEXT = z3.Context()
# Bound memory while retaining translations reused across nearby extraction roots.
_SMT_CACHE_CAPACITY = 4096
_SMT_CACHE: OrderedDict[tuple[type, int], tuple[Any, z3.ExprRef]] = OrderedDict()


def clear_smt_translation_cache() -> None:
    """Drop memoized Claripy-to-Z3 AST pairs between independent roots."""
    _SMT_CACHE.clear()


def _remember_smt_translation(
    key: tuple[type, int], ast: Any, expression: z3.ExprRef
) -> None:
    _SMT_CACHE[key] = (ast, expression)
    _SMT_CACHE.move_to_end(key)
    if len(_SMT_CACHE) > _SMT_CACHE_CAPACITY:
        _SMT_CACHE.popitem(last=False)
_U64_MAX = (1 << 64) - 1

_angr = runtime.angr
_claripy = runtime.claripy
_angr_ccall = importlib.import_module("angr.engines.vex.claripy.ccall")


_AMD64_OP_COPY: int = _angr_ccall.data["AMD64"]["OpTypes"][
    "G_CC_OP_COPY"
]
_AMD64_FLAG_BIT: dict[str, int] = {
    "CF": _angr_ccall.data["AMD64"]["CondBitOffsets"]["G_CC_SHIFT_C"],
    "PF": _angr_ccall.data["AMD64"]["CondBitOffsets"]["G_CC_SHIFT_P"],
    "AF": _angr_ccall.data["AMD64"]["CondBitOffsets"]["G_CC_SHIFT_A"],
    "ZF": _angr_ccall.data["AMD64"]["CondBitOffsets"]["G_CC_SHIFT_Z"],
    "SF": _angr_ccall.data["AMD64"]["CondBitOffsets"]["G_CC_SHIFT_S"],
    "OF": _angr_ccall.data["AMD64"]["CondBitOffsets"]["G_CC_SHIFT_O"],
}


@dataclass(frozen=True)
class CanonicalDeclaration:
    name: str
    sort: str
    width: int
    index_width: int | None = None


@dataclass(frozen=True, eq=False)
class MemoryWrite:
    address: z3.BitVecRef
    value: z3.BitVecRef
    size: int


@dataclass(frozen=True)
class InstructionOutcome:
    outcome_id: int
    guard: z3.BoolRef
    updates: Mapping[str, z3.ExprRef]
    target: z3.BitVecRef
    target_value: int | None
    jumpkind: str
    writes: tuple[MemoryWrite, ...]


@dataclass(frozen=True)
class InstructionOutcomeFamily:
    source: int
    source_guard: z3.BoolRef
    outcomes: tuple[InstructionOutcome, ...]


def _u64(value: Any, field: str) -> int:
    if type(value) is not int or not 0 <= value <= _U64_MAX:
        raise Amd64AdapterError(f"{field} must be an unsigned 64-bit integer")
    return value


def canonical_declarations(arch: Any | None = None) -> tuple[CanonicalDeclaration, ...]:
    layout = AMD64_LAYOUT if arch is None else architecture_layout(arch)
    return (
        tuple(
            CanonicalDeclaration(item.name, "bv", item.bits)
            for item in layout.storage if item.name not in NORMALIZED_AMD64_FLAGS
        )
        + tuple(
            CanonicalDeclaration(f"rflags_{name}", "bv", 1)
            for name in FLAG_NAMES
        )
        + (CanonicalDeclaration(MEMORY_NAME, "array", 8, layout.address_bits),)
    )


def declaration(name: str) -> CanonicalDeclaration:
    for item in canonical_declarations():
        if item.name == name:
            return item
    raise Amd64AdapterError(f"unknown canonical AMD64 declaration {name!r}")


@cache
def canonical_register(name: str) -> z3.BitVecRef:
    if name not in REGISTER_NAMES:
        raise Amd64AdapterError(f"unknown canonical AMD64 register {name!r}")
    return z3.BitVec(name, AMD64_LAYOUT.register(name).bits, ctx=LTS_EXTRACTION_CONTEXT)


@cache
def canonical_register_view(name: str) -> z3.BitVecRef:
    """Read a metadata-derived alias without introducing independent state."""
    try:
        view = AMD64_LAYOUT.view(name)
        backing = canonical_register(view.storage_name)
    except (StopIteration, Amd64AdapterError) as error:
        raise Amd64AdapterError(f"register view {name!r} has no independent canonical backing") from error
    if view.size_bytes * 8 == backing.size():
        return backing
    low = view.byte_offset * 8
    if AMD64_LAYOUT.register_endness == "Iend_BE":
        low = backing.size() - low - view.size_bytes * 8
    return z3.Extract(low + view.size_bytes * 8 - 1, low, backing)


@cache
def canonical_flag(name: str) -> z3.BitVecRef:
    if name not in FLAG_NAMES:
        raise Amd64AdapterError(f"unknown canonical AMD64 flag {name!r}")
    return z3.BitVec(
        f"rflags_{name}",
        1,
        ctx=LTS_EXTRACTION_CONTEXT,
    )


@cache
def canonical_memory() -> z3.ArrayRef:
    address = z3.BitVecSort(AMD64_LAYOUT.address_bits, ctx=LTS_EXTRACTION_CONTEXT)
    byte = z3.BitVecSort(8, ctx=LTS_EXTRACTION_CONTEXT)
    return z3.Array(MEMORY_NAME, address, byte)


def claripy_to_z3(ast: Any) -> z3.ExprRef:
    """Cross the Angr boundary into the dedicated extraction context."""

    key = (type(ast), ast.hash())
    cached = _SMT_CACHE.get(key)
    if cached is not None and ast.identical(cached[0]):
        _SMT_CACHE.move_to_end(key)
        return cached[1]
    if ast.op == "BoolV":
        expression = z3.BoolVal(_claripy.is_true(ast), ctx=LTS_EXTRACTION_CONTEXT)
        _remember_smt_translation(key, ast, expression)
        return expression
    # Public self-contained SMT export supplies declarations and preserves
    # symbol names; Z3 parses it directly into the extraction context.
    result_name = "__wruh_smt_result"
    while result_name in ast.variables:
        result_name += "_"
    result = (_claripy.BoolS(result_name, explicit_name=True)
              if isinstance(ast, _claripy.ast.Bool) else
              _claripy.BVS(result_name, ast.size(), explicit_name=True))
    transport = _claripy.Solver()
    transport.add(result == ast)
    smt = transport.to_smt2()
    try:
        formula = z3.parse_smt2_string(smt, ctx=LTS_EXTRACTION_CONTEXT)
    except z3.Z3Exception as error:
        raise Amd64AdapterError(f"public Angr SMT export failed to parse: {error}\n{smt}") from error
    if len(formula) != 1 or not z3.is_eq(formula[0]):
        raise Amd64AdapterError("Angr SMT export did not retain the result equality")
    lhs, rhs = formula[0].children()
    expression = rhs if str(lhs) == result_name else lhs
    if str(lhs) != result_name and str(rhs) != result_name:
        raise Amd64AdapterError("Angr SMT export lost the result symbol")
    _remember_smt_translation(key, ast, expression)
    return expression


def load_le(
    memory: z3.ArrayRef,
    address: z3.BitVecRef,
    size: int,
) -> z3.BitVecRef:
    """Load one byte-aligned little-endian value from canonical memory."""

    _require_memory_shape(memory, address)
    if type(size) is not int or size <= 0:
        raise Amd64AdapterError("memory access size must be positive")
    bytes_high_to_low = tuple(
        z3.Select(
            memory,
            address + z3.BitVecVal(
                offset,
                64,
                ctx=LTS_EXTRACTION_CONTEXT,
            ),
        )
        for offset in reversed(range(size))
    )
    if len(bytes_high_to_low) == 1:
        return bytes_high_to_low[0]
    return z3.Concat(*bytes_high_to_low)


def store_le(
    memory: z3.ArrayRef,
    address: z3.BitVecRef,
    value: z3.BitVecRef,
    size: int,
) -> z3.ArrayRef:
    """Store one byte-aligned little-endian value into canonical memory."""

    _require_memory_shape(memory, address)
    if (
        type(size) is not int
        or size <= 0
        or not z3.is_bv(value)
        or value.ctx != LTS_EXTRACTION_CONTEXT
        or value.size() != size * 8
    ):
        raise Amd64AdapterError("memory store value has the wrong width")
    result = memory
    for offset in range(size):
        result = z3.Store(
            result,
            address + z3.BitVecVal(
                offset,
                64,
                ctx=LTS_EXTRACTION_CONTEXT,
            ),
            z3.Extract(offset * 8 + 7, offset * 8, value),
        )
    return result


def _require_memory_shape(
    memory: z3.ArrayRef,
    address: z3.BitVecRef,
) -> None:
    if (
        not z3.is_array(memory)
        or memory.ctx != LTS_EXTRACTION_CONTEXT
        or memory.domain().size() != 64
        or memory.range().size() != 8
        or not z3.is_bv(address)
        or address.ctx != LTS_EXTRACTION_CONTEXT
        or address.size() != 64
    ):
        raise Amd64AdapterError(
            "memory and address must be extraction-context BV64-to-BV8/BV64"
        )


def source_rip_guard(source: int) -> z3.BoolRef:
    source = _u64(source, "source")
    return canonical_register(AMD64_LAYOUT.ip_view) == z3.BitVecVal(
        source,
        AMD64_LAYOUT.address_bits,
        ctx=LTS_EXTRACTION_CONTEXT,
    )


def require_mirrored_rip(
    target: z3.ExprRef,
    post_rip: z3.ExprRef,
) -> None:
    if (
        not z3.is_bv(target)
        or not z3.is_bv(post_rip)
        or target.size() != 64
        or post_rip.size() != 64
        or target.ctx != LTS_EXTRACTION_CONTEXT
        or post_rip.ctx != LTS_EXTRACTION_CONTEXT
    ):
        raise Amd64AdapterError(
            "target and post-rip must be extraction-context BV64 expressions"
        )
    solver = z3.Solver(ctx=LTS_EXTRACTION_CONTEXT)
    solver.add(target != post_rip)
    if solver.check() != z3.unsat:
        raise Amd64AdapterError("target and post-rip disagree semantically")


def _seed_flag_bvs() -> dict[str, Any]:
    return {
        name: _claripy.BVS(
            f"rflags_{name}",
            1,
            explicit_name=True,
        )
        for name in FLAG_NAMES
    }


def _initial_cc_dep1(flag_bvs: Mapping[str, Any]) -> Any:
    pieces: list[Any] = []
    next_bit = 63
    for name, bit in sorted(
        _AMD64_FLAG_BIT.items(),
        key=lambda item: -item[1],
    ):
        if next_bit > bit:
            pieces.append(_claripy.BVV(0, next_bit - bit))
        pieces.append(flag_bvs[name])
        next_bit = bit - 1
    if next_bit >= 0:
        pieces.append(_claripy.BVV(0, next_bit + 1))
    return _claripy.Concat(*pieces)


def _access_size(value: Any, field: str) -> int:
    try:
        size = int(value) if not hasattr(value, "op") else (
            int(value.args[0]) if value.op == "BVV" else 0
        )
    except (TypeError, ValueError):
        size = 0
    if size <= 0:
        raise Amd64AdapterError(f"{field} has unknown or invalid width")
    return size


def _preserve_symbolic_memory_addresses(state: Any) -> None:
    """Keep hooked memory accesses parametric in their symbolic addresses."""

    if state.inspect.address_concretization_action in {"load", "store"}:
        state.inspect.address_concretization_add_constraints = False


def _apply_typed_z3_replacements(state: Any, expression: z3.ExprRef) -> z3.ExprRef:
    """Resolve summary placeholders for adapter-side address classification."""

    replacements = state.globals.get("_ghot_typed_replacements", {})
    if not replacements:
        return expression
    from ayxg.substitution import substitute_expr
    from ayxg.z3 import expr_from_z3, expr_to_z3

    typed = expr_from_z3(expression)
    for _ in range(len(replacements) + 1):
        replaced = substitute_expr(typed, replacements)
        if replaced is typed or replaced == typed:
            break
        typed = replaced
    variables = {
        **{name: canonical_register(name) for name in REGISTER_NAMES},
        **{
            f"rflags_{name}": canonical_flag(name)
            for name in FLAG_NAMES
        },
        MEMORY_NAME: canonical_memory(),
    }
    return expr_to_z3(typed, variables, LTS_EXTRACTION_CONTEXT)


def _memory_read_hook(state: Any) -> None:
    address = state.inspect.mem_read_address
    if address is None:
        raise Amd64AdapterError("memory read is missing its address")
    if state.inspect.mem_read_expr is not None:
        raise Amd64AdapterError("memory read already has a value before loading")
    size = _access_size(state.inspect.mem_read_length, "memory read")

    address_z3 = claripy_to_z3(address)
    classified_address_z3 = _apply_typed_z3_replacements(state, address_z3)

    def record(kind: str) -> None:
        events = tuple(state.globals.get("_ghot_memory_read_events", ()))
        state.globals["_ghot_memory_read_events"] = events + (
            (kind, size, str(z3.simplify(classified_address_z3))),
        )

    fixed_bytes = []
    for offset in range(size):
        byte_address = classified_address_z3 + z3.BitVecVal(
            offset,
            classified_address_z3.size(),
            ctx=LTS_EXTRACTION_CONTEXT,
        )
        matches = [
            value
            for expected, value in state.globals.get("_ghot_fixed_byte_reads", ())
            if z3.is_true(z3.simplify(byte_address == expected))
        ]
        if len(matches) > 1:
            raise Amd64AdapterError("memory read matches multiple fixed input bytes")
        if not matches:
            fixed_bytes = []
            break
        fixed_bytes.append(matches[0])
    if fixed_bytes:
        little_endian = sum(
            value << (offset * 8)
            for offset, value in enumerate(fixed_bytes)
        )
        state.inspect.mem_read_expr = _claripy.BVV(little_endian, size * 8)
        record("fixed")
        counts = dict(state.globals.get("_ghot_memory_read_counts", {}))
        counts["fixed"] = counts.get("fixed", 0) + 1
        state.globals["_ghot_memory_read_counts"] = counts
        return

    record("symbolic")
    counts = dict(state.globals.get("_ghot_memory_read_counts", {}))
    counts["symbolic"] = counts.get("symbolic", 0) + 1
    state.globals["_ghot_memory_read_counts"] = counts
    placeholders = dict(state.globals.get("_ghot_memory_reads", {}))
    name = f"__ghot_memory_read_{len(placeholders)}__"
    placeholder = _claripy.BVS(name, size * 8, explicit_name=True)
    placeholders[name] = (
        address,
        size,
        state.globals["_ghot_memory_expr"],
    )
    state.globals["_ghot_memory_reads"] = placeholders
    state.inspect.mem_read_expr = placeholder


def _memory_write_hook(state: Any) -> None:
    address = state.inspect.mem_write_address
    value = state.inspect.mem_write_expr
    if address is None or value is None:
        raise Amd64AdapterError("memory write is missing address or value")
    size = _access_size(state.inspect.mem_write_length, "memory write")
    address_z3 = claripy_to_z3(address)
    value_z3 = claripy_to_z3(value)
    current = state.globals["_ghot_memory_expr"]
    updated = store_le(current, address_z3, value_z3, size)
    writes = list(state.globals.get("_ghot_memory_writes", ()))
    writes.append(MemoryWrite(address_z3, value_z3, size))
    state.globals["_ghot_memory_expr"] = updated
    state.globals["_ghot_memory_writes"] = tuple(writes)


# VEX represents these architectural finite selectors in larger BV storage.
# Splitting is demand-driven: integer instructions do not pay the FP cross-product.
_SELECTOR_DOMAINS = {
    "d": (1, (1 << 64) - 1),
    "sseround": tuple(range(4)),
    "fpround": tuple(range(4)),
    "ftop": tuple(range(8)),
}
_SELECTOR_MASKS = {"ftop": 7}


class _SelectorSplitRequired(Exception):
    def __init__(self, name: str):
        self.name = name
        super().__init__(name)


def _selector_read_hook(state: Any) -> None:
    if not state.globals.get("_wruh_capture_selectors", False):
        return
    offset = state.inspect.reg_read_offset
    if hasattr(offset, "op"):
        if offset.op != "BVV":
            raise Amd64AdapterError("symbolic register-file offset cannot identify selector domain")
        offset = int(offset.args[0])
    size = _access_size(state.inspect.reg_read_length, "register read")
    for name in _SELECTOR_DOMAINS:
        item = AMD64_LAYOUT.register(name)
        if offset < item.offset + item.size_bytes and item.offset < offset + size:
            expression = state.inspect.reg_read_expr
            if expression is not None and expression.symbolic:
                if name in state.globals.get("_wruh_selector_assignments", {}) and name in _SELECTOR_MASKS:
                    # A modular selector retains its raw counter high bits.
                    # VEX computes its slot modulo8, simplifying the low bits.
                    continue
                if name in state.globals.get("_wruh_selector_assignments", {}):
                    raise Amd64AdapterError(
                        f"selector {name} became symbolic inside one instruction; exact splitting unavailable")
                raise _SelectorSplitRequired(name)


def fresh_instruction_state(
    project: Any, source: int, *, selector_assignments: Mapping[str, int] | None = None,
) -> Any:
    """Create the canonical symbolic pre-state for one real instruction."""

    source = _u64(source, "source")
    if project.arch.name != "AMD64" or project.arch.bits != 64:
        raise Amd64AdapterError(
            f"unexpected architecture: {project.arch.name}/{project.arch.bits}"
        )
    state = project.factory.blank_state(addr=source)
    state.options.add(_angr.options.NO_IP_CONCRETIZATION)
    state.options.add(_angr.options.PRODUCE_ZERODIV_SUCCESSORS)
    state.options.add(_angr.options.TRACK_MEMORY_ACTIONS)
    state.options.add(_angr.options.TRACK_REGISTER_ACTIONS)
    state.options.add(_angr.options.SYMBOLIC_WRITE_ADDRESSES)
    state.options.add(_angr.options.UNDER_CONSTRAINED_SYMEXEC)
    state.options.discard(_angr.options.UNICORN)
    layout = architecture_layout(project.arch)
    if layout != AMD64_LAYOUT:
        raise Amd64AdapterError("project architecture layout differs from canonical declaration layout")
    state.globals["_wruh_architecture_layout"] = layout
    for item in layout.storage:
        if item.name in NORMALIZED_AMD64_FLAGS:
            continue
        state.registers.store(item.offset, _claripy.BVS(item.name, item.bits, explicit_name=True),
                              size=item.size_bytes, endness=project.arch.register_endness)
    state.registers.store(project.arch.ip_offset, _claripy.BVV(source, project.arch.bits),
                          size=project.arch.bytes, endness=project.arch.register_endness)

    assignments = dict(selector_assignments or {})
    for name, selected in assignments.items():
        if name not in _SELECTOR_DOMAINS or selected not in _SELECTOR_DOMAINS[name]:
            raise Amd64AdapterError(f"invalid explicit selector assignment {name}={selected}")
        item = layout.register(name)
        symbol = _claripy.BVS(name, item.bits, explicit_name=True)
        mask = _SELECTOR_MASKS.get(name)
        if mask is None:
            chosen = _claripy.BVV(selected, item.bits)
            state.add_constraints(symbol == selected)
        else:
            state.add_constraints((symbol & mask) == selected)
            chosen = (symbol & ((1 << item.bits) - 1 - mask)) | selected
        state.registers.store(item.offset, chosen, size=item.size_bytes,
                              endness=project.arch.register_endness)
    state.globals["_wruh_selector_assignments"] = assignments
    state.globals["_wruh_capture_selectors"] = True
    state.inspect.b("reg_read", when=_angr.BP_AFTER, action=_selector_read_hook)

    flag_bvs = _seed_flag_bvs()
    state.regs.cc_op = _claripy.BVV(_AMD64_OP_COPY, 64)
    state.regs.cc_dep1 = _initial_cc_dep1(flag_bvs)
    state.regs.cc_dep2 = _claripy.BVV(0, 64)
    state.regs.cc_ndep = _claripy.BVV(0, 64)
    state.globals["_ghot_flag_bvs"] = flag_bvs
    state.globals["_ghot_memory_expr"] = canonical_memory()
    state.globals["_ghot_memory_reads"] = {}
    state.globals["_ghot_memory_writes"] = ()
    state.inspect.b(
        "address_concretization",
        when=_angr.BP_BEFORE,
        action=_preserve_symbolic_memory_addresses,
    )
    state.inspect.b(
        "mem_read",
        when=_angr.BP_BEFORE,
        action=_memory_read_hook,
    )
    state.inspect.b(
        "mem_write",
        when=_angr.BP_AFTER,
        action=_memory_write_hook,
    )
    return state


def install_typed_summary_state(
    state: Any,
    updates: Mapping[str, Any],
    *,
    continuation: int,
) -> None:
    """Install one already-composed typed summary without re-executing it."""

    continuation = _u64(continuation, "summary continuation")
    if set(updates) != set(CANONICAL_NAMES):
        missing = sorted(set(CANONICAL_NAMES) - set(updates))
        extra = sorted(set(updates) - set(CANONICAL_NAMES))
        raise Amd64AdapterError(
            f"summary update domain changed: missing={missing}, extra={extra}"
        )

    index = int(state.globals.get("_ghot_summary_state_index", 0))
    state.globals["_ghot_summary_state_index"] = index + 1
    prefix = f"ghot_summary_{index}"
    replacements = dict(state.globals.get("_ghot_typed_replacements", {}))

    for item in AMD64_LAYOUT.storage:
        if item.name in NORMALIZED_AMD64_FLAGS or item.name == AMD64_LAYOUT.ip_view:
            continue
        synthetic_name = f"{prefix}_{item.name}__"
        if synthetic_name in replacements:
            raise Amd64AdapterError("summary register placeholder is not fresh")
        state.registers.store(item.offset, _claripy.BVS(synthetic_name, item.bits, explicit_name=True),
                              size=item.size_bytes, endness=state.arch.register_endness)
        replacements[synthetic_name] = updates[item.name]

    flag_bvs = {}
    for name in FLAG_NAMES:
        synthetic_name = f"{prefix}_rflags_{name}__"
        if synthetic_name in replacements:
            raise Amd64AdapterError("summary flag placeholder is not fresh")
        flag_bvs[name] = _claripy.BVS(
            synthetic_name,
            1,
            explicit_name=True,
        )
        replacements[synthetic_name] = updates[f"rflags_{name}"]
    state.regs.cc_op = _claripy.BVV(_AMD64_OP_COPY, 64)
    state.regs.cc_dep1 = _initial_cc_dep1(flag_bvs)
    state.regs.cc_dep2 = _claripy.BVV(0, 64)
    state.regs.cc_ndep = _claripy.BVV(0, 64)
    state.globals["_ghot_flag_bvs"] = flag_bvs

    memory_name = f"{prefix}_{MEMORY_NAME}__"
    if memory_name in replacements:
        raise Amd64AdapterError("summary memory placeholder is not fresh")
    memory = z3.Array(
        memory_name,
        canonical_memory().sort().domain(),
        canonical_memory().sort().range(),
    )
    replacements[memory_name] = updates[MEMORY_NAME]
    state.globals["_ghot_memory_expr"] = memory
    state.globals["_ghot_typed_replacements"] = replacements
    state.registers.store(state.arch.ip_offset, _claripy.BVV(continuation, state.arch.bits),
                          size=state.arch.bytes, endness=state.arch.register_endness)


def _resolve_memory_reads(
    expression: z3.ExprRef,
    reads: Mapping[str, tuple[Any, int, z3.ArrayRef]],
) -> z3.ExprRef:
    replacements: list[tuple[z3.ExprRef, z3.ExprRef]] = []
    for name, (address, size, memory_at_read) in reads.items():
        address_z3 = claripy_to_z3(address)
        if replacements:
            address_z3 = z3.substitute(address_z3, *replacements)
            memory_at_read = z3.substitute(memory_at_read, *replacements)
        placeholder = z3.BitVec(
            name,
            size * 8,
            ctx=LTS_EXTRACTION_CONTEXT,
        )
        replacements.append(
            (placeholder, load_le(memory_at_read, address_z3, size))
        )
    if replacements:
        return z3.substitute(expression, *replacements)
    return expression


def _post_flag_updates(
    post: Any,
    source: int,
    reads: Mapping[str, tuple[Any, int, z3.ArrayRef]],
) -> dict[str, z3.ExprRef]:
    from angr.errors import SimCCallError, SimError

    errors: tuple[type[BaseException], ...] = (SimError, SimCCallError)
    try:
        from angr.errors import CCallMultivaluedException

        errors += (CCallMultivaluedException,)
    except ImportError:
        pass

    try:
        post_rflags = post.regs.rflags
    except errors as exc:
        raise Amd64AdapterError(
            f"instruction at {source:#x} has unsupported flag state"
        ) from exc

    updates: dict[str, z3.ExprRef] = {}
    for name in FLAG_NAMES:
        bit = _AMD64_FLAG_BIT[name]
        value = _resolve_memory_reads(
            claripy_to_z3(_claripy.Extract(bit, bit, post_rflags)),
            reads,
        )
        if not value.eq(canonical_flag(name)):
            updates[f"rflags_{name}"] = value
    return updates


def _post_updates(post: Any, source: int) -> dict[str, z3.ExprRef]:
    reads = post.globals.get("_ghot_memory_reads", {})
    updates: dict[str, z3.ExprRef] = {}
    for item in AMD64_LAYOUT.storage:
        if item.name in NORMALIZED_AMD64_FLAGS or item.name == AMD64_LAYOUT.ip_view:
            continue
        value = _resolve_memory_reads(
            claripy_to_z3(post.registers.load(item.offset, size=item.size_bytes,
                                            endness=post.arch.register_endness)), reads)
        if not value.eq(canonical_register(item.name)):
            updates[item.name] = value
    updates.update(_post_flag_updates(post, source, reads))
    return updates


def _resolved_writes(post: Any) -> tuple[MemoryWrite, ...]:
    reads = post.globals.get("_ghot_memory_reads", {})
    return tuple(
        MemoryWrite(
            _resolve_memory_reads(write.address, reads),
            _resolve_memory_reads(write.value, reads),
            write.size,
        )
        for write in post.globals.get("_ghot_memory_writes", ())
    )


def _symbolic_target_update(
    post: Any,
    updates: dict[str, z3.ExprRef],
) -> tuple[z3.BitVecRef, int | None]:
    target = _resolve_memory_reads(
        claripy_to_z3(post.registers.load(post.arch.ip_offset, size=post.arch.bytes,
                                       endness=post.arch.register_endness)),
        post.globals.get("_ghot_memory_reads", {}),
    )
    if not z3.is_bv(target) or target.size() != 64:
        raise Amd64AdapterError("instruction target is not BV64")
    updates[AMD64_LAYOUT.ip_view] = target
    require_mirrored_rip(target, updates[AMD64_LAYOUT.ip_view])
    simplified = z3.simplify(target)
    target_value = (
        simplified.as_long() if z3.is_bv_value(simplified) else None
    )
    return target, target_value


class _EngineFallbackCapture(logging.Handler):
    """Fail closed if the public engine reports a symbolic-rounding fallback."""
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage()
        if "symbolic rounding mode found" in message:
            self.messages.append(message)


def step_instruction_outcomes(
    project: Any,
    source: int,
) -> InstructionOutcomeFamily:
    """Translate the complete successor relation of one real instruction."""
    source = _u64(source, "source")
    block = project.factory.block(source, num_inst=1)
    decoded_instruction = block.capstone.insns
    if (
        len(decoded_instruction) == 1
        and decoded_instruction[0].address == source
        and decoded_instruction[0].size == 2
        and is_ud2_instruction(
            {
                "mnemonic": decoded_instruction[0].mnemonic,
                "bytes": decoded_instruction[0].bytes.hex(),
                "size": decoded_instruction[0].size,
            }
        )
    ):
        # UD2 has no normal successor: its sole architectural result is #UD.
        return InstructionOutcomeFamily(
            source,
            source_rip_guard(source),
            (
                InstructionOutcome(
                    outcome_id=0,
                    guard=z3.BoolVal(True, ctx=LTS_EXTRACTION_CONTEXT),
                    updates={},
                    target=z3.BitVecVal(source, 64, ctx=LTS_EXTRACTION_CONTEXT),
                    target_value=source,
                    jumpkind="Ijk_SigILL",
                    writes=(),
                ),
            ),
        )
    if block.vex.instructions != 1 or len(block.capstone.insns) != 1:
        raise Amd64AdapterError(f"expected one decoded instruction at {source:#x}")
    pending: list[dict[str, int]] = [{}]
    successors = []
    while pending:
        assignments = pending.pop(0)
        state = fresh_instruction_state(project, source, selector_assignments=assignments)
        capture = _EngineFallbackCapture()
        logger = logging.getLogger("angr.engines.vex.claripy.irop")
        logger.addHandler(capture)
        try:
            try:
                selected_successors = project.factory.successors(state, num_inst=1).all_successors
            except _SelectorSplitRequired as split:
                pending[0:0] = [dict(assignments, **{split.name: value})
                                for value in _SELECTOR_DOMAINS[split.name]]
                continue
            if capture.messages:
                raise Amd64AdapterError(
                    f"instruction at {source:#x} requested unsupported symbolic rounding: {capture.messages}")
        finally:
            logger.removeHandler(capture)
        for post in selected_successors:
            post.globals["_wruh_capture_selectors"] = False
        successors.extend(selected_successors)
    if not successors:
        raise Amd64AdapterError(f"instruction at {source:#x} has no outcomes")
    outcomes = []
    for outcome_id, post in enumerate(successors):
        reads = post.globals.get("_ghot_memory_reads", {})
        constraints = [
            _resolve_memory_reads(claripy_to_z3(c), reads)
            for c in post.solver.constraints
        ]
        guard = (z3.And(*constraints) if constraints else
                 z3.BoolVal(True, ctx=LTS_EXTRACTION_CONTEXT))
        updates = _post_updates(post, source)
        writes = _resolved_writes(post)
        if writes:
            updates[MEMORY_NAME] = _resolve_memory_reads(
                post.globals["_ghot_memory_expr"], reads,
            )
        target, target_value = _symbolic_target_update(post, updates)
        outcomes.append(InstructionOutcome(
            outcome_id=outcome_id,
            guard=guard,
            updates=updates,
            target=target,
            target_value=target_value,
            jumpkind=post.history.jumpkind,
            writes=writes,
        ))
    return InstructionOutcomeFamily(source, source_rip_guard(source), tuple(outcomes))
