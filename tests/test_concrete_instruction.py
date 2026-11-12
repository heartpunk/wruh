"""Concrete evaluator properties; no solver is used to choose inputs."""
import platform
import sys
import pytest

# The native PBT runtime and pinned iced wheel target Linux x86-64.
if sys.platform != 'linux' or platform.machine() not in ('x86_64', 'amd64'):
    pytest.skip('native PBT tests require Linux x86-64', allow_module_level=True)

from types import SimpleNamespace
from functools import cache
from hypothesis import given, settings, strategies as st
import z3
from extractor.concrete_instruction import IncompleteEvaluation, evaluate_instruction
from extractor.native_state_compare import ConcreteState, StateDomain


def relation(update, writes=()):
    return SimpleNamespace(guard=z3.BoolVal(True), updates=update, writes=writes, jumpkind='Ijk_Boring', outcome_id=0)


@given(st.integers(0, 255), st.integers(0, 255))
def test_simultaneous_register_and_memory_update(x, byte):
    r = z3.BitVec('test_rax', 64)
    m = z3.Array('test_mem', z3.BitVecSort(64), z3.BitVecSort(8))
    address = z3.BitVecVal(0x1000, 64)
    value = z3.Extract(7, 0, r)
    write = SimpleNamespace(address=address, value=value, size=1)
    out = relation({'rax': r + 1, 'mem': z3.Store(m, address, value)}, (write,))
    state = ConcreteState({'rax': x}, {0x1000: byte})
    domain = StateDomain({'rax': 64}, frozenset({0x1000}))
    result = evaluate_instruction(SimpleNamespace(source_guard=z3.BoolVal(True), outcomes=(out,)), {'rax': r}, m, state, domain)
    assert result.state.registers == {'rax': x + 1}
    assert result.state.memory == {0x1000: x}
    assert (result.jumpkind, result.outcome_id) == ('Ijk_Boring', 0)


def test_missing_memory_read_fails_closed():
    r = z3.BitVec('test_rax', 64)
    m = z3.Array('test_mem', z3.BitVecSort(64), z3.BitVecSort(8))
    out = relation({'rax': z3.ZeroExt(56, z3.Select(m, z3.BitVecVal(0x1001, 64)))})
    try:
        evaluate_instruction(SimpleNamespace(source_guard=z3.BoolVal(True), outcomes=(out,)), {'rax': r}, m,
                             ConcreteState({'rax': 0}, {0x1000: 0}),
                             StateDomain({'rax': 64}, frozenset({0x1000})))
    except IncompleteEvaluation:
        pass
    else:
        raise AssertionError('unmapped memory became concrete')


def test_false_source_guard_fails_closed():
    r = z3.BitVec('test_rax', 64)
    m = z3.Array('test_mem', z3.BitVecSort(64), z3.BitVecSort(8))
    family = SimpleNamespace(source_guard=r == 1, outcomes=(relation({}),))
    try:
        evaluate_instruction(family, {'rax': r}, m, ConcreteState({'rax': 0}, {}),
                             StateDomain({'rax': 64}, frozenset()))
    except IncompleteEvaluation:
        pass
    else:
        raise AssertionError('false source guard was accepted')


@cache
def _mov_family():
    from extractor import runtime
    from extractor.amd64_state import step_instruction_outcomes
    project = runtime.angr.load_shellcode(bytes.fromhex('4889d8'), arch='amd64', load_address=0x400000)
    return step_instruction_outcomes(project, 0x400000)


@settings(deadline=None)
@given(st.integers(0, 2**64 - 1), st.integers(0, 2**64 - 1))
def test_existing_extractor_relation_transfers_concrete_registers(rax, rbx):
    """Exercise the real extraction/evaluation boundary without native execution."""
    from extractor.amd64_state import (canonical_declarations, canonical_flag,
                                       canonical_memory, canonical_register)
    declarations = canonical_declarations()
    symbols = {d.name: (canonical_flag(d.name.removeprefix('rflags_'))
                        if d.name.startswith('rflags_') else canonical_register(d.name))
               for d in declarations if d.name != 'mem'}
    domain = StateDomain({d.name: d.width for d in declarations if d.name != 'mem'}, frozenset())
    registers = {name: 0 for name in domain.registers}
    registers.update(rip=0x400000, rax=rax, rbx=rbx)
    result = evaluate_instruction(_mov_family(), symbols, canonical_memory(), ConcreteState(registers, {}), domain)
    assert result.state.registers['rax'] == rbx
    assert result.state.registers['rbx'] == rbx


def test_aliasing_erases_operand_roles_in_a_concrete_extraction():
    """A no-op seed cannot serve as a general register-binding template."""
    from extractor import runtime
    from extractor.amd64_state import step_instruction_outcomes
    project = runtime.angr.load_shellcode(bytes.fromhex('4889c0'), arch='amd64', load_address=0x400000)
    same_register = step_instruction_outcomes(project, 0x400000)
    different_registers = _mov_family()
    assert 'rax' not in same_register.outcomes[0].updates
    assert 'rax' in different_registers.outcomes[0].updates
