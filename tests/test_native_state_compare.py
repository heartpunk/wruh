"""Properties of the strict concrete-state comparator."""
import platform
import sys
import pytest

# The native PBT runtime and pinned iced wheel target Linux x86-64.
if sys.platform != 'linux' or platform.machine() not in ('x86_64', 'amd64'):
    pytest.skip('native PBT tests require Linux x86-64', allow_module_level=True)

from hypothesis import given, strategies as st
from extractor.native_state_compare import ConcreteState, StateDomain, compare_states

DOMAIN = StateDomain({'rax': 64, 'rflags_CF': 1}, frozenset({0x1000, 0x1001}))


@given(st.integers(0, 2**64 - 1), st.integers(0, 1),
       st.integers(0, 255), st.integers(0, 255))
def test_reflexive_and_detects_every_changed_component(rax, cf, first, second):
    state = ConcreteState({'rax': rax, 'rflags_CF': cf}, {0x1000: first, 0x1001: second})
    assert compare_states(state, state, DOMAIN)['status'] == 'MATCH'
    for name in DOMAIN.registers:
        changed = dict(state.registers)
        changed[name] ^= 1
        result = compare_states(state, ConcreteState(changed, state.memory), DOMAIN)
        assert result['status'] == 'MISMATCH' and set(result['registers']) == {name}
    for address in DOMAIN.memory_addresses:
        changed = dict(state.memory)
        changed[address] ^= 1
        result = compare_states(state, ConcreteState(state.registers, changed), DOMAIN)
        assert result['status'] == 'MISMATCH' and set(result['memory']) == {address}


def test_missing_or_out_of_range_values_fail_closed():
    valid = ConcreteState({'rax': 0, 'rflags_CF': 0}, {0x1000: 0, 0x1001: 0})
    for bad in (ConcreteState({'rax': 0}, valid.memory),
                ConcreteState(valid.registers, {0x1000: 0}),
                ConcreteState({'rax': 2**64, 'rflags_CF': 0}, valid.memory),
                ConcreteState(valid.registers, {0x1000: 256, 0x1001: 0})):
        try:
            compare_states(valid, bad, DOMAIN)
        except ValueError:
            pass
        else:
            raise AssertionError('invalid state was accepted')
