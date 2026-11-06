"""Evaluate a previously extracted instruction relation on a concrete state.

This evaluator never asks a solver for an input. Unspecified memory remains
symbolic, so a read outside the supplied domain fails instead of becoming zero.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import z3

from extractor.native_state_compare import ConcreteState, StateDomain


@dataclass(frozen=True)
class ConcreteOutcome:
    state: ConcreteState
    jumpkind: str
    outcome_id: int


class IncompleteEvaluation(ValueError):
    """The relation or supplied state cannot produce an exact concrete result."""


def evaluate_instruction(family: Any, symbols: Mapping[str, Any],
                         memory_symbol: Any, state: ConcreteState,
                         domain: StateDomain) -> ConcreteOutcome:
    """Apply exactly one enabled outcome, rejecting incomplete state/effects.

    `symbols` must cover every register in the supplied domain; `family` is
    the relation returned by `step_instruction_outcomes`.
    """
    if set(symbols) != set(domain.registers) or set(state.registers) != set(symbols):
        raise IncompleteEvaluation('incomplete register domain')
    if set(state.memory) != domain.memory_addresses:
        raise IncompleteEvaluation('incomplete memory domain')
    if (not z3.is_array(memory_symbol)
            or not z3.is_bv_sort(memory_symbol.sort().domain())
            or not z3.is_bv_sort(memory_symbol.sort().range())
            or memory_symbol.sort().domain().size() != 64
            or memory_symbol.sort().range().size() != 8):
        raise IncompleteEvaluation('memory symbol must be an array from BV64 to BV8')
    context = memory_symbol.ctx
    unmapped = z3.FreshConst(memory_symbol.sort(), prefix='wruh_unmapped_memory')
    # Represent known zero-filled regions compactly while keeping every address
    # outside the declared domain symbolic. Nonzero bytes are stored below.
    ranges = []
    for address in sorted(domain.memory_addresses):
        if ranges and address == ranges[-1][1] + 1:
            ranges[-1] = (ranges[-1][0], address)
        else:
            ranges.append((address, address))
    index = z3.FreshConst(z3.BitVecSort(64, ctx=context), prefix='wruh_memory_index')
    in_domain = (z3.Or(*(z3.And(z3.UGE(index, z3.BitVecVal(lo, 64, ctx=context)),
                                z3.ULE(index, z3.BitVecVal(hi, 64, ctx=context)))
                         for lo, hi in ranges)) if ranges else z3.BoolVal(False, ctx=context))
    memory = z3.Lambda(index, z3.If(in_domain, z3.BitVecVal(0, 8, ctx=context),
                                    z3.Select(unmapped, index)))
    substitutions = []
    for name, symbol in symbols.items():
        width = domain.registers[name]
        value = state.registers[name]
        if (not z3.is_bv(symbol) or symbol.ctx != context or symbol.size() != width
                or type(value) is not int or not 0 <= value < 2**width):
            raise IncompleteEvaluation(f'invalid register {name}')
        substitutions.append((symbol, z3.BitVecVal(value, width, ctx=context)))
    for address, value in state.memory.items():
        if type(value) is not int or not 0 <= value < 256:
            raise IncompleteEvaluation('invalid memory byte')
        if value:
            memory = z3.Store(memory, z3.BitVecVal(address, 64, ctx=context),
                              z3.BitVecVal(value, 8, ctx=context))
    substitutions.append((memory_symbol, memory))

    def resolve(expression: Any) -> Any:
        return z3.simplify(z3.substitute(expression, *substitutions))

    if not z3.is_true(resolve(family.source_guard)):
        raise IncompleteEvaluation('source guard is false or symbolic')
    enabled = []
    for outcome in family.outcomes:
        guard = resolve(outcome.guard)
        if z3.is_true(guard):
            enabled.append(outcome)
        elif not z3.is_false(guard):
            raise IncompleteEvaluation('guard depends on missing or symbolic state')
    if len(enabled) != 1:
        raise IncompleteEvaluation(f'expected one enabled outcome, found {len(enabled)}')
    outcome = enabled[0]
    if not isinstance(outcome.jumpkind, str) or not outcome.jumpkind or type(outcome.outcome_id) is not int:
        raise IncompleteEvaluation('outcome is missing its control-flow classification')
    unknown_updates = set(outcome.updates) - set(symbols) - {'mem'}
    if unknown_updates:
        raise IncompleteEvaluation(f'unknown updated fields: {sorted(unknown_updates)}')
    if bool(outcome.writes) != ('mem' in outcome.updates):
        raise IncompleteEvaluation('memory update and write descriptions disagree')
    expected_memory = memory
    for write in outcome.writes:
        address = resolve(write.address)
        if not z3.is_bv_value(address) or type(write.size) is not int or write.size <= 0:
            raise IncompleteEvaluation('memory write address or size is not concrete')
        if any((address.as_long() + offset) % 2**64 not in domain.memory_addresses
               for offset in range(write.size)):
            raise IncompleteEvaluation('memory write extends outside supplied domain')
        value = resolve(write.value)
        if not z3.is_bv_value(value) or value.size() != write.size * 8:
            raise IncompleteEvaluation('memory write value is not concrete')
        for offset in range(write.size):
            a = (address.as_long() + offset) % 2**64
            expected_memory = z3.Store(expected_memory, z3.BitVecVal(a, 64, ctx=context),
                                       z3.BitVecVal((value.as_long() >> (8 * offset)) & 255, 8, ctx=context))
    registers = dict(state.registers)
    for name, expression in outcome.updates.items():
        if name == 'mem':
            continue
        value = resolve(expression)
        if not z3.is_bv_value(value) or value.size() != domain.registers[name]:
            raise IncompleteEvaluation(f'non-concrete update: {name}')
        registers[name] = value.as_long()
    result_memory = dict(state.memory)
    if 'mem' in outcome.updates:
        updated_memory = resolve(outcome.updates['mem'])
        if not z3.is_true(z3.simplify(updated_memory == expected_memory)):
            raise IncompleteEvaluation('memory update cannot be reconciled with recorded writes')
        for address in domain.memory_addresses:
            byte = z3.simplify(z3.Select(updated_memory, z3.BitVecVal(address, 64, ctx=context)))
            if not z3.is_bv_value(byte):
                raise IncompleteEvaluation(f'non-concrete memory at {address:#x}')
            result_memory[address] = byte.as_long()
    return ConcreteOutcome(ConcreteState(registers, result_memory), outcome.jumpkind, outcome.outcome_id)
