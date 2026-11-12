"""Concrete bindings get distinct models, reused across input states."""
import platform
import sys
import pytest

if sys.platform != 'linux' or platform.machine() not in ('x86_64', 'amd64'):
    pytest.skip('native PBT tests require Linux x86-64', allow_module_level=True)

import iced_x86 as ice
from extractor.catalogue_models import prepare_model


def test_binding_reextracts_and_exact_encoding_is_cached():
    encoded = bytes.fromhex('4889d8')
    row = {'iform': 'MOV_GPRv_GPRv_89', 'iced_code': ice.Decoder(64, encoded).decode().code,
           'bytes': encoded.hex(), 'bitness': 64, 'operand_width': 64}
    identify = lambda _: row['iform']
    identify.operand_width = lambda _: 64
    seed = prepare_model(row, identify)
    bound = prepare_model(row, identify, bindings={'op0_register': ice.Register.RCX})
    again = prepare_model(row, identify, bindings={'op0_register': ice.Register.RCX})
    assert bound.encoded != seed.encoded
    assert bound.relation is not seed.relation
    assert again.relation is bound.relation


def test_xed_operand_width_must_match_catalogue():
    from extractor.iform_candidates import CandidateError
    encoded = bytes.fromhex('4889d8')
    row = {'iform': 'MOV_GPRv_GPRv_89', 'iced_code': ice.Decoder(64, encoded).decode().code,
           'bytes': encoded.hex(), 'bitness': 64, 'operand_width': 64}
    def identify(_encoded):
        return row['iform']
    identify.operand_width = lambda _encoded: 32
    with pytest.raises(CandidateError, match='operand width'):
        prepare_model(row, identify)


@pytest.mark.parametrize(('hex_bytes', 'iform', 'binding'), [
    ('4883c001', 'ADD_GPRv_IMMb', {'immediate8to64': 2}),
    ('488b448b10', 'MOV_GPRv_MEMv', {'memory_displacement': 32}),
])
def test_immediate_and_address_changes_reextract(hex_bytes, iform, binding):
    encoded = bytes.fromhex(hex_bytes)
    row = {'iform': iform, 'iced_code': ice.Decoder(64, encoded).decode().code,
           'bytes': hex_bytes, 'bitness': 64, 'operand_width': 64}
    identify = lambda _: iform
    identify.operand_width = lambda _: 64
    seed = prepare_model(row, identify)
    changed = prepare_model(row, identify, bindings=binding)
    assert changed.encoded != seed.encoded
    assert changed.relation is not seed.relation
