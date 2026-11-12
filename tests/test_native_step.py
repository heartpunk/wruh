"""Properties of the native runner request and pre-state transfer."""
import platform
import sys
import pytest

if sys.platform != 'linux' or platform.machine() not in ('x86_64', 'amd64'):
    pytest.skip('native PBT tests require Linux x86-64', allow_module_level=True)

from pathlib import Path
from unittest.mock import patch
from hypothesis import given, strategies as st
from extractor.native_step import REGISTERS, capture_step
from extractor.isolated_native import NativeIsolationError


def fake_capture(_bwrap, _runner, _runtime, request):
    requested = request['registers']
    before = dict(requested, rip=0x400000, eflags=requested['eflags'] | 0x202)
    fpstate = bytearray(512)
    fpstate[160:416] = bytes.fromhex(request['xmm'])
    return {'before': before, 'after': dict(before), 'signal': 5, 'signal_code': 2,
            'xstate_format': 2, 'before_xstate': fpstate.hex(), 'after_xstate': fpstate.hex(),
            'data': '00' * 4096, 'stack': '00' * 4096,
            'extra1_base': request['extra1_base'], 'extra2_base': request['extra2_base'],
            'extra1': '00' * (4096 if request['extra1_base'] else 0),
            'extra2': '00' * (4096 if request['extra2_base'] else 0),
            'code': (bytes.fromhex(request['bytes']) + bytes(4096 - len(bytes.fromhex(request['bytes'])))).hex()}


@given(st.integers(0, 2**64 - 1), st.integers(0, 2**64 - 1), st.binary(min_size=256, max_size=256))
def test_register_and_segment_bases_are_transferred(rax, base, xmm):
    registers = {name: 0 for name in REGISTERS}
    registers['rax'] = rax
    with patch('extractor.native_step.run_isolated', side_effect=fake_capture):
        result = capture_step(Path('/bwrap'), Path('/runner'), (), b'\x90', registers, 0,
                              bytes(8192), fs_base=base, gs_base=base, xmm=xmm)
    assert result['before']['rax'] == rax
    assert result['before']['fs_base'] == result['before']['gs_base'] == base
    assert bytes.fromhex(result['before_xstate'])[160:416] == xmm


def test_mismatched_native_prestate_is_incomplete():
    registers = {name: 0 for name in REGISTERS}
    def corrupt(*args):
        result = fake_capture(*args)
        result['before']['rax'] = 1
        return result
    with patch('extractor.native_step.run_isolated', side_effect=corrupt):
        with pytest.raises(NativeIsolationError):
            capture_step(Path('/bwrap'), Path('/runner'), (), b'\x90', registers, 0, bytes(8192))


def test_extra_pages_are_planned_for_outside_and_cross_page_accesses():
    from extractor.native_step import _extra_pages
    encoded = bytes.fromhex('488b03')
    assert _extra_pages(encoded, {'rbx': 0x500000}) == (0x500000,)
    assert _extra_pages(encoded, {'rbx': 0x500fff}) == (0x500000, 0x501000)


def test_low_or_noncanonical_extra_page_is_rejected():
    from extractor.native_memory_scope import MemoryScopeError
    from extractor.native_step import _extra_pages
    with pytest.raises(MemoryScopeError):
        _extra_pages(bytes.fromhex('488b03'), {'rbx': 0})
    with pytest.raises(MemoryScopeError):
        _extra_pages(bytes.fromhex('488b03'), {'rbx': 0xffff800000000000})
