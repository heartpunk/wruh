"""State comparison properties for the exact native capture protocol."""
import platform
import sys
import pytest

if sys.platform != 'linux' or platform.machine() not in ('x86_64', 'amd64'):
    pytest.skip('native PBT tests require Linux x86-64', allow_module_level=True)

from functools import cache
from types import SimpleNamespace
from hypothesis import given, settings, strategies as st
from extractor.native_state_differential import compare_native_state
from extractor.native_step import REGISTERS


@cache
def mov_model():
    from extractor import runtime
    from extractor.amd64_state import step_instruction_outcomes
    encoded = bytes.fromhex('4889d8')
    project = runtime.angr.load_shellcode(encoded, arch='amd64', load_address=0x400000)
    return SimpleNamespace(encoded=encoded, source=0x400000,
                           relation=step_instruction_outcomes(project, 0x400000))


def capture(rax, rbx):
    before = {name: 0 for name in REGISTERS}
    before.update(rax=rax, rbx=rbx, rip=0x400000, eflags=0x202,
                  cs=0, ss=0, ds=0, es=0, fs=0, gs=0, fs_base=0, gs_base=0)
    after = dict(before, rax=rbx, rip=0x400003)
    return {'before': before, 'after': after, 'signal': 5, 'signal_code': 2,
            'before_xstate': '00' * 512, 'after_xstate': '00' * 512,
            'data': '00' * 4096, 'stack': '00' * 4096,
            'extra1_base': 0, 'extra2_base': 0, 'extra1': '', 'extra2': '',
            'code': (bytes.fromhex('4889d8') + bytes(4093)).hex()}


@settings(max_examples=10, deadline=None)
@given(st.integers(0, 2**64 - 1), st.integers(0, 2**64 - 1))
def test_match_and_register_mismatch(rax, rbx):
    native = capture(rax, rbx)
    assert compare_native_state(mov_model(), native, bytes(8192))['status'] == 'MATCH'
    native['after']['rax'] ^= 1
    assert compare_native_state(mov_model(), native, bytes(8192))['status'] == 'MISMATCH'


def test_changed_extended_state_is_incomplete():
    native = capture(0, 1)
    native['after_xstate'] = '01' + '00' * 511
    assert compare_native_state(mov_model(), native, bytes(8192))['status'] == 'INCOMPLETE'


def test_undefined_flags_are_reported_but_defined_flags_are_compared():
    from extractor import runtime
    from extractor.amd64_state import step_instruction_outcomes
    encoded = bytes.fromhex('4831c0')
    project = runtime.angr.load_shellcode(encoded, arch='amd64', load_address=0x400000)
    model = SimpleNamespace(encoded=encoded, source=0x400000,
                            relation=step_instruction_outcomes(project, 0x400000))
    native = capture(1, 0)
    native['code'] = (encoded + bytes(4096 - len(encoded))).hex()
    native['after']['rax'] = 0
    native['after']['eflags'] = 0x246
    result = compare_native_state(model, native, bytes(8192))
    assert result['status'] == 'MATCH'
    assert result['undefined_flags'] == ['AF']
    native['after']['eflags'] ^= 1 << 4
    result = compare_native_state(model, native, bytes(8192))
    assert result['status'] == 'MATCH'
    assert 'rflags_AF' in result['undefined_differences']
    native['after']['eflags'] ^= 1
    assert compare_native_state(model, native, bytes(8192))['status'] == 'MISMATCH'


def test_direction_flag_is_transferred_to_model():
    native = capture(0, 1)
    native['before']['eflags'] |= 1 << 10
    native['after']['eflags'] |= 1 << 10
    assert compare_native_state(mov_model(), native, bytes(8192))['status'] == 'MATCH'


def test_fxsave_xmm_state_is_compared():
    from extractor import runtime
    from extractor.amd64_state import step_instruction_outcomes
    encoded = bytes.fromhex('660fefc0')
    project = runtime.angr.load_shellcode(encoded, arch='amd64', load_address=0x400000)
    model = SimpleNamespace(encoded=encoded, source=0x400000,
                            relation=step_instruction_outcomes(project, 0x400000))
    native = capture(0, 0)
    native['code'] = (encoded + bytes(4096 - len(encoded))).hex()
    native['after']['rip'] = 0x400004
    initial = bytearray(512)
    initial[160:176] = b'\x11' * 16
    native['xstate_format'] = 2
    native['before_xstate'] = initial.hex()
    native['after_xstate'] = bytes(512).hex()
    assert compare_native_state(model, native, bytes(8192))['status'] == 'MATCH'
    corrupt = bytearray(512)
    corrupt[160] = 1
    native['after_xstate'] = corrupt.hex()
    assert compare_native_state(model, native, bytes(8192))['status'] == 'MISMATCH'


def test_divide_fault_is_compared_as_an_outcome():
    from extractor import runtime
    from extractor.amd64_state import step_instruction_outcomes
    encoded = bytes.fromhex('48f7f9')
    project = runtime.angr.load_shellcode(encoded, arch='amd64', load_address=0x400000)
    model = SimpleNamespace(encoded=encoded, source=0x400000,
                            relation=step_instruction_outcomes(project, 0x400000))
    native = capture(0, 0)
    native['code'] = (encoded + bytes(4096 - len(encoded))).hex()
    native['after'] = dict(native['before'])
    native['after']['eflags'] |= 1 << 16
    native['signal'] = 8
    native['signal_code'] = 1
    result = compare_native_state(model, native, bytes(8192))
    assert result['status'] == 'MATCH'
    assert result['jumpkind'] == 'Ijk_SigFPE_IntDiv'
    native['after']['eflags'] &= ~(1 << 16)
    assert compare_native_state(model, native, bytes(8192))['status'] == 'MISMATCH'


def test_memory_write_is_compared_byte_for_byte():
    from extractor import runtime
    from extractor.amd64_state import step_instruction_outcomes
    encoded = bytes.fromhex('488903')
    project = runtime.angr.load_shellcode(encoded, arch='amd64', load_address=0x400000)
    model = SimpleNamespace(encoded=encoded, source=0x400000,
                            relation=step_instruction_outcomes(project, 0x400000))
    native = capture(0x12345678, 0x100000)
    native['code'] = (encoded + bytes(4096 - len(encoded))).hex()
    native['after']['rax'] = native['before']['rax']
    page = bytearray(4096)
    page[:8] = (0x12345678).to_bytes(8, 'little')
    native['data'] = page.hex()
    assert compare_native_state(model, native, bytes(8192))['status'] == 'MATCH'
    page[7] ^= 1
    native['data'] = page.hex()
    assert compare_native_state(model, native, bytes(8192))['status'] == 'MISMATCH'


@pytest.mark.parametrize(('prefix', 'segment'), [('64', 'fs_base'), ('65', 'gs_base')])
def test_segment_base_memory_load_is_transferred(prefix, segment):
    from extractor import runtime
    from extractor.amd64_state import step_instruction_outcomes
    encoded = bytes.fromhex(prefix + '488b042500000000')
    project = runtime.angr.load_shellcode(encoded, arch='amd64', load_address=0x400000)
    model = SimpleNamespace(encoded=encoded, source=0x400000,
                            relation=step_instruction_outcomes(project, 0x400000))
    native = capture(0, 0)
    native['code'] = (encoded + bytes(4096 - len(encoded))).hex()
    native['before'][segment] = native['after'][segment] = 0x100000
    native['after']['rip'] = 0x400000 + len(encoded)
    native['after']['rax'] = 0x12345678
    memory = bytearray(8192)
    memory[:8] = (0x12345678).to_bytes(8, 'little')
    native['data'] = bytes(memory[:4096]).hex()
    assert compare_native_state(model, native, bytes(memory))['status'] == 'MATCH'


def test_extra_page_write_is_compared_byte_for_byte():
    from extractor import runtime
    from extractor.amd64_state import step_instruction_outcomes
    encoded = bytes.fromhex('488903')
    project = runtime.angr.load_shellcode(encoded, arch='amd64', load_address=0x400000)
    model = SimpleNamespace(encoded=encoded, source=0x400000,
                            relation=step_instruction_outcomes(project, 0x400000))
    native = capture(0x12345678, 0x500000)
    native['code'] = (encoded + bytes(4096 - len(encoded))).hex()
    native['after']['rax'] = native['before']['rax']
    native['extra1_base'] = 0x500000
    page = bytearray(4096)
    page[:8] = (0x12345678).to_bytes(8, 'little')
    native['extra1'] = page.hex()
    assert compare_native_state(model, native, bytes(8192))['status'] == 'MATCH'
    page[7] ^= 1
    native['extra1'] = page.hex()
    assert compare_native_state(model, native, bytes(8192))['status'] == 'MISMATCH'
