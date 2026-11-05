import platform
import sys
import pytest

# The native PBT runtime and pinned iced wheel target Linux x86-64.
if sys.platform != 'linux' or platform.machine() not in ('x86_64', 'amd64'):
    pytest.skip('native PBT tests require Linux x86-64', allow_module_level=True)

from hypothesis import given, strategies as st
import iced_x86 as ice
from extractor.iform_candidates import CandidateError, CandidateTemplate

SEED = bytes.fromhex('4889d8')
CODE = ice.Decoder(64, SEED).decode().code
TEMPLATE = CandidateTemplate('MOV_GPRv_GPRv_89', CODE, SEED)


@given(st.sampled_from([ice.Register.RAX, ice.Register.RCX, ice.Register.RDX,
                        ice.Register.RBX, ice.Register.RSP, ice.Register.RBP,
                        ice.Register.RSI, ice.Register.RDI, ice.Register.R8,
                        ice.Register.R9, ice.Register.R10, ice.Register.R11,
                        ice.Register.R12, ice.Register.R13, ice.Register.R14,
                        ice.Register.R15]))
def test_register_binding_roundtrips(reg):
    encoded = TEMPLATE.generate({'op0_register': reg}, lambda _: TEMPLATE.iform)
    decoded = ice.Decoder(64, encoded).decode()
    assert decoded.op0_register == reg
    assert decoded.op1_register == ice.Register.RBX


def test_changed_iform_is_not_accepted():
    try:
        TEMPLATE.generate({}, lambda _: 'different')
    except CandidateError:
        pass
    else:
        raise AssertionError('wrong iform was accepted')


@given(st.integers(-128, 127))
def test_signed_immediate_binding_roundtrips(value):
    seed = bytes.fromhex('4883c001')
    ins = ice.Decoder(64, seed).decode()
    template = CandidateTemplate('ADD_GPRv_IMMb', ins.code, seed)
    encoded = template.generate({'immediate8to64': value}, lambda _: template.iform)
    assert ice.Decoder(64, encoded).decode().immediate8to64 == value


def test_unrelated_operand_binding_is_rejected():
    for binding in ({'immediate8': 0}, {'memory_base': ice.Register.RAX}):
        try:
            TEMPLATE.generate(binding, lambda _: TEMPLATE.iform)
        except CandidateError:
            pass
        else:
            raise AssertionError('binding unrelated to an operand was accepted')


def test_operand_inspection_surfaces_fields():
    from extractor.iform_candidates import inspect_operands
    assert inspect_operands(TEMPLATE) == {
        'fields': ['op0_register', 'op1_register'], 'unsupported_operands': []}
    seed = bytes.fromhex('4883c001')
    code = ice.Decoder(64, seed).decode().code
    result = inspect_operands(CandidateTemplate('ADD_GPRv_IMMb', code, seed))
    assert result == {'fields': ['immediate8to64', 'op0_register'],
                      'unsupported_operands': []}


@given(st.sampled_from([ice.Register.RAX, ice.Register.RCX, ice.Register.RDX,
                        ice.Register.RBX, ice.Register.RSP, ice.Register.RBP,
                        ice.Register.RSI, ice.Register.RDI, ice.Register.R8,
                        ice.Register.R9, ice.Register.R10, ice.Register.R11,
                        ice.Register.R12, ice.Register.R13, ice.Register.R14,
                        ice.Register.R15]),
       st.sampled_from([ice.Register.RAX, ice.Register.RCX, ice.Register.RDX,
                        ice.Register.RBX, ice.Register.RBP, ice.Register.RSI,
                        ice.Register.RDI, ice.Register.R8, ice.Register.R9,
                        ice.Register.R10, ice.Register.R11, ice.Register.R12,
                        ice.Register.R13, ice.Register.R14, ice.Register.R15]),
       st.sampled_from([1, 2, 4, 8]), st.integers(1, 127))
def test_memory_address_bindings_roundtrip(base, index, scale, displacement):
    seed = bytes.fromhex('488b448b10')
    code = ice.Decoder(64, seed).decode().code
    template = CandidateTemplate('MOV_GPRv_MEMv', code, seed)
    bindings = {'memory_base': base, 'memory_index': index,
                'memory_index_scale': scale, 'memory_displacement': displacement,
                'memory_displ_size': 1}
    encoded = template.generate(bindings, lambda _: template.iform)
    decoded = ice.Decoder(64, encoded).decode()
    assert all(getattr(decoded, name) == value for name, value in bindings.items())


@given(st.integers(-(2**31), 2**31 - 1))
def test_wide_memory_displacements_roundtrip(displacement):
    seed = bytes.fromhex('488b448b10')
    code = ice.Decoder(64, seed).decode().code
    template = CandidateTemplate('MOV_GPRv_MEMv', code, seed)
    value = displacement & (2**64 - 1)
    encoded = template.generate({'memory_displacement': value, 'memory_displ_size': 8},
                                lambda _: template.iform)
    decoded = ice.Decoder(64, encoded).decode()
    assert decoded.memory_displacement == value and decoded.memory_displ_size == 8
