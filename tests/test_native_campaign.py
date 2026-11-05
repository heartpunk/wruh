"""Property tests for catalogue candidate and initial-state construction."""
import platform
import sys
import pytest

if sys.platform != 'linux' or platform.machine() not in ('x86_64', 'amd64'):
    pytest.skip('native PBT tests require Linux x86-64', allow_module_level=True)

import iced_x86 as ice
from hypothesis import given, strategies as st
from extractor.native_catalogue_campaign import _candidate_registers, _register_bindings, _operand_strategy, _encoding_database, _address_registers, _source_fingerprint
from extractor.native_memory_scope import memory_accesses
from extractor.native_step import REGISTERS


def test_register_bindings_include_each_operand():
    bindings = _register_bindings(bytes.fromhex('4889d8'))
    assert {} in bindings
    assert {'op0_register': ice.Register.RCX} in bindings
    assert {'op1_register': ice.Register.RDX} in bindings


@given(st.integers(0, 2**64 - 1))
def test_memory_base_is_constructed_without_a_solver(value):
    registers = {name: value for name in REGISTERS}
    registers = _candidate_registers(bytes.fromhex('488b03'), registers)
    assert memory_accesses(bytes.fromhex('488b03'), registers) == ((0x100800, 8),)
    assert registers['rsp'] == value


@given(st.data())
def test_structured_strategy_produces_single_field_bindings(data):
    encoded = bytes.fromhex('488b448b10')
    row = {'iform': 'MOV_GPRv_MEMv', 'iced_code': ice.Decoder(64, encoded).decode().code,
           'bytes': encoded.hex(), 'bitness': 64}
    binding = data.draw(_operand_strategy(row))
    assert len(binding) <= 2
    if len(binding) == 2:
        assert set(binding) == {'memory_displacement', 'memory_displ_size'}
    assert not binding or next(iter(binding)) in {
        'op0_register', 'memory_base', 'memory_index', 'memory_index_scale',
        'memory_displacement', 'memory_displ_size'}


def test_row_deadline_stops_only_its_worker():
    import time
    from types import SimpleNamespace
    from unittest.mock import patch
    from extractor.native_catalogue_campaign import _run_with_deadline
    def stalled(_row, _args, sender):
        sender.send(('PROGRESS', {'input': 17}))
        time.sleep(10)
    with patch('extractor.native_catalogue_campaign._row_worker', stalled):
        status, detail = _run_with_deadline({}, SimpleNamespace(row_seconds=1))
    assert status == 'INCOMPLETE' and 'deadline exceeded' in detail and '17' in detail


def test_examples_do_not_leak_between_encoding_databases(tmp_path):
    first = _encoding_database(tmp_path, 'MOV_GPRv_GPRv_89', '4889d8')
    second = _encoding_database(tmp_path, 'MOV_GPRv_GPRv_89', '4889c8')
    first.save(b'property', b'example')
    assert list(first.fetch(b'property')) == [b'example']
    assert list(second.fetch(b'property')) == []


def test_invalid_worker_status_is_incomplete():
    from types import SimpleNamespace
    from unittest.mock import patch
    from extractor.native_catalogue_campaign import _run_with_deadline
    def invalid(_row, _args, sender):
        sender.send(('UNKNOWN', 'invalid'))
        sender.close()
    with patch('extractor.native_catalogue_campaign._row_worker', invalid):
        status, detail = _run_with_deadline({}, SimpleNamespace(row_seconds=5))
    assert status == 'INCOMPLETE' and 'invalid result' in detail


def test_campaign_preflight_rejects_missing_resource_boundary():
    from unittest.mock import patch
    from extractor.isolated_native import NativeIsolationError
    from extractor.native_catalogue_campaign import main
    arguments = ['campaign', '/catalogue', '--xed', '/xed', '--bwrap', '/bwrap',
                 '--runner', '/runner', '--runtime', '/nix/store/runtime',
                 '--source-revision', 'a' * 40]
    with patch('sys.argv', arguments), patch('os.access', return_value=True), \
         patch('pathlib.Path.is_file', return_value=True), \
         patch('extractor.native_catalogue_campaign.bubblewrap_command'), \
         patch('extractor.native_catalogue_campaign.require_bounded_cgroup',
               side_effect=NativeIsolationError('missing cgroup')), \
         patch('extractor.native_catalogue_campaign.multiprocessing.get_context') as workers:
        with pytest.raises(NativeIsolationError, match='missing cgroup'):
            main()
        workers.assert_not_called()


def test_address_binding_respects_32_bit_address_size():
    instruction = ice.Decoder(64, bytes.fromhex('67488b448b10')).decode()
    registers, ip, stack = _address_registers(instruction)
    assert ice.Register.EAX in registers and ice.Register.RAX not in registers
    assert ip == ice.Register.EIP and stack == ice.Register.ESP


def test_address_setup_accounts_for_segment_base_and_32_bit_wrap():
    values = {name: 0 for name in REGISTERS}
    encoded = bytes.fromhex('6467488b03')
    registers = _candidate_registers(encoded, values, fs_base=0x100000)
    accesses = memory_accesses(encoded, {**registers, 'fs_base': 0x100000})
    assert accesses == ((0x100800, 8),)


def test_stack_pointer_is_bounded_when_used_as_address():
    registers = _candidate_registers(bytes.fromhex('50'), {name: 0 for name in REGISTERS})
    assert registers['rsp'] == 0x200800


@pytest.mark.parametrize('hex_bytes', ['488b0400', '488b0440', '488b440001'])
def test_aliased_base_and_index_are_placed_in_data_page(hex_bytes):
    encoded = bytes.fromhex(hex_bytes)
    registers = _candidate_registers(encoded, {name: 0 for name in REGISTERS})
    accesses = memory_accesses(encoded, registers)
    assert len(accesses) == 1
    assert 0x100800 <= accesses[0][0] <= 0x100807


def test_source_fingerprint_changes_with_source_and_rejects_missing_file(tmp_path):
    required = ['extractor/a.py', 'corpus/native/step_runner.c', 'corpus/BUILD.bazel',
                'extractor/BUILD.bazel', 'flake.nix', 'flake.lock', 'MODULE.bazel',
                'MODULE.bazel.lock', 'BUILD.bazel', '.bazelrc']
    for name in required:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name)
    first = _source_fingerprint(tmp_path)
    (tmp_path / 'extractor/a.py').write_text('changed')
    assert _source_fingerprint(tmp_path) != first
    (tmp_path / 'flake.lock').unlink()
    with pytest.raises(RuntimeError, match='provenance file missing'):
        _source_fingerprint(tmp_path)
