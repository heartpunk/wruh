"""Properties of memory-domain checks for the native runner."""
import platform
import sys
import pytest

if sys.platform != 'linux' or platform.machine() not in ('x86_64', 'amd64'):
    pytest.skip('native PBT tests require Linux x86-64', allow_module_level=True)

from hypothesis import given, strategies as st
from extractor.native_memory_scope import MemoryScopeError, memory_accesses


@given(st.integers(0, 4088))
def test_memory_operand_within_page(offset):
    assert memory_accesses(bytes.fromhex('488b03'), {'rbx': 0x100000 + offset}) == ((0x100000 + offset, 8),)


def test_memory_operand_outside_page_rejected():
    with pytest.raises(MemoryScopeError):
        memory_accesses(bytes.fromhex('488b03'), {'rbx': 0x100ffc})


def test_push_uses_predecrement_stack_address():
    assert memory_accesses(bytes.fromhex('50'), {'rax': 0, 'rsp': 0x200800}) == ((0x2007f8, 8),)


def test_register_only_has_no_memory():
    assert memory_accesses(bytes.fromhex('4889d8'), {'rax': 1, 'rbx': 2}) == ()


def test_code_page_reads_are_observed_but_writes_are_rejected():
    registers = {'rip': 0x400007, 'rax': 0}
    assert memory_accesses(bytes.fromhex('488b05f9ffffff'), registers) == ((0x400000, 8),)
    with pytest.raises(MemoryScopeError):
        memory_accesses(bytes.fromhex('488905f9ffffff'), registers)


def test_access_can_span_adjacent_extra_pages():
    encoded = bytes.fromhex('488b03')
    assert memory_accesses(encoded, {'rbx': 0x500fff},
                           extra_ranges=((0x500000, 0x501000), (0x501000, 0x502000))) == ((0x500fff, 8),)


def test_repeated_memory_instruction_is_explicitly_incomplete():
    with pytest.raises(MemoryScopeError, match='multi-access'):
        memory_accesses(bytes.fromhex('f3a4'), {'rsi': 0x100000, 'rdi': 0x200000})
