"""Prepare existing WRUH instruction relations at exact catalogue encodings.

Relations are extracted once per seed and reused across concrete input states.
No claim is made that a relation covers a different operand encoding.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Callable, Mapping

from extractor.iform_candidates import CandidateBindingError, CandidateError, CandidateTemplate

SOURCE = 0x400000


@dataclass(frozen=True)
class EncodingModel:
    iform: str
    iced_code: int
    encoded: bytes
    source: int
    relation: Any


@lru_cache(maxsize=64)
def _extract(encoded: bytes, source: int) -> Any:
    from extractor import runtime
    from extractor.amd64_state import step_instruction_outcomes

    project = runtime.angr.load_shellcode(encoded, arch='amd64', load_address=source)
    return step_instruction_outcomes(project, source)


def prepare_model(row: Mapping[str, Any], identify_iform: Callable[[bytes], str],
                  source: int = SOURCE, *, bindings: Mapping[str, int] | None = None) -> EncodingModel:
    """Validate a catalogue row and extract its exact instruction relation."""
    encoded = bytes.fromhex(row['bytes'])
    template = CandidateTemplate(row['iform'], row['iced_code'], encoded, row['bitness'])
    operand_width = row['operand_width']
    if type(operand_width) is not int or operand_width < 0:
        raise CandidateError('catalogued operand width is invalid')
    if not hasattr(identify_iform, 'operand_width'):
        raise CandidateError('XED operand-width check is unavailable')
    if identify_iform.operand_width(encoded) != operand_width:
        raise CandidateError('catalogued seed changed XED operand width')
    candidate = template.generate(bindings or {}, identify_iform, ip=source)
    # Even a no-binding re-encoding may be byte-different; retain the original
    # catalogue seed in that case. Each mutated candidate gets its own exact
    # extraction and can then be reused for multiple concrete states.
    if not bindings:
        candidate = encoded
    if identify_iform.operand_width(candidate) != operand_width:
        raise CandidateBindingError('candidate changed XED operand width')
    return EncodingModel(row['iform'], row['iced_code'], candidate, source,
                         _extract(candidate, source))
