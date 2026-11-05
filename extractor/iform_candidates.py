"""Structured, checked mutations of a catalogued x86 instruction encoding.

This is a candidate generator, not an instruction semantics model. Rejected
bindings are reported to the caller instead of being silently filtered.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

import iced_x86 as ice


class CandidateError(ValueError):
    """A proposed binding is not representable or changes the catalogued form."""


# Explicit allowlist prevents writes to decoded fields with unrelated meaning.
_MEMORY_FIELDS = frozenset({'memory_base', 'memory_index', 'memory_index_scale',
                            'memory_displacement', 'memory_displ_size'})
_OPERAND_FIELDS = {name.lower(): getattr(ice.OpKind, name) for name in (
    'IMMEDIATE8', 'IMMEDIATE8_2ND', 'IMMEDIATE16', 'IMMEDIATE32',
    'IMMEDIATE64', 'IMMEDIATE8TO16', 'IMMEDIATE8TO32', 'IMMEDIATE8TO64',
    'IMMEDIATE32TO64', 'NEAR_BRANCH16', 'NEAR_BRANCH32', 'NEAR_BRANCH64')}
_REGISTER_FIELDS = frozenset(f'op{i}_register' for i in range(5))
_FIELDS = _MEMORY_FIELDS | frozenset(_OPERAND_FIELDS) | _REGISTER_FIELDS


@dataclass(frozen=True)
class CandidateTemplate:
    iform: str
    iced_code: int
    seed: bytes
    bitness: int = 64

    def generate(self, bindings: Mapping[str, int], identify_iform: Callable[[bytes], str],
                 ip: int = 0x400000) -> bytes:
        if self.bitness != 64 or not self.seed or len(self.seed) > 15:
            raise CandidateError('invalid catalogued seed or bitness')
        if set(bindings) - _FIELDS:
            raise CandidateError('unknown binding fields: ' + ', '.join(sorted(set(bindings) - _FIELDS)))
        decoder = ice.Decoder(self.bitness, self.seed, ip=ip)
        ins = decoder.decode()
        if ins.is_invalid or ins.len != len(self.seed) or ins.code != self.iced_code:
            raise CandidateError('catalogued seed does not decode to its recorded iced Code')
        if identify_iform(self.seed) != self.iform:
            raise CandidateError('catalogued seed does not decode to its recorded XED iform')
        try:
            for name, value in bindings.items():
                if type(value) is not int:
                    raise CandidateError(f'{name} must be an integer')
                if name in _REGISTER_FIELDS:
                    index = int(name[2])
                    if index >= ins.op_count or ins.op_kind(index) != ice.OpKind.REGISTER:
                        raise CandidateError(f'{name} does not name a register operand')
                elif name in _OPERAND_FIELDS:
                    if _OPERAND_FIELDS[name] not in (ins.op_kind(i) for i in range(ins.op_count)):
                        raise CandidateError(f'{name} is not an operand of this instruction')
                elif name in _MEMORY_FIELDS:
                    if ice.OpKind.MEMORY not in (ins.op_kind(i) for i in range(ins.op_count)):
                        raise CandidateError(f'{name} requires an explicit memory operand')
                setattr(ins, name, value)
            encoder = ice.Encoder(self.bitness)
            encoder.encode(ins, ip)
            result = bytes(encoder.take_buffer())
        except (ValueError, OverflowError) as exc:
            raise CandidateError(f'invalid operand binding: {exc}') from exc
        decoded = ice.Decoder(self.bitness, result, ip=ip).decode()
        if decoded.is_invalid or decoded.len != len(result) or decoded.code != self.iced_code:
            raise CandidateError('generated instruction changed iced Code')
        for name, value in bindings.items():
            if getattr(decoded, name) != value:
                raise CandidateError(f'{name} did not survive encoding and decoding')
        if identify_iform(result) != self.iform:
            raise CandidateError('generated instruction changed XED iform')
        return result


def xed_iform_decoder(executable: str, *, timeout: float = 2.0) -> Callable[[bytes], str]:
    """Create a fail-closed adapter for the XED single-instruction decoder."""
    import re
    import subprocess

    def classify(data: bytes) -> tuple[str, int]:
        if not data or len(data) > 15:
            raise CandidateError('XED input must be one to fifteen bytes')
        try:
            result = subprocess.run([executable], input=data.hex() + '\n', check=True, text=True,
                                    capture_output=True, timeout=timeout)
        except (OSError, subprocess.SubprocessError) as exc:
            raise CandidateError(f'XED decoder failed: {exc}') from exc
        fields = result.stdout.strip().split('\t')
        if len(fields) != 2 or not fields[1].isdigit():
            raise CandidateError('XED returned invalid classification fields')
        name = fields[0]
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', name):
            raise CandidateError('XED returned an invalid iform name')
        return name, int(fields[1])

    def identify(data: bytes) -> str:
        return classify(data)[0]

    identify.operand_width = lambda data: classify(data)[1]  # type: ignore[attr-defined]

    return identify


def inspect_operands(template: CandidateTemplate, ip: int = 0x400000) -> dict:
    """Describe representable fields and surface unhandled operand kinds.

    This describes the generator interface, not a completeness claim about
    possible encodings or the instruction's implicit architectural effects.
    """
    decoder = ice.Decoder(template.bitness, template.seed, ip=ip)
    ins = decoder.decode()
    if ins.is_invalid or ins.len != len(template.seed) or ins.code != template.iced_code:
        raise CandidateError('catalogued seed does not decode to its recorded iced Code')
    fields = []
    unsupported = []
    kind_to_field = {kind: name for name, kind in _OPERAND_FIELDS.items()}
    for index in range(ins.op_count):
        kind = ins.op_kind(index)
        if kind == ice.OpKind.REGISTER:
            fields.append(f'op{index}_register')
        elif kind == ice.OpKind.MEMORY:
            fields.extend(sorted(_MEMORY_FIELDS))
        elif kind in kind_to_field:
            fields.append(kind_to_field[kind])
        else:
            unsupported.append({'index': index, 'iced_op_kind': kind})
    return {'fields': sorted(set(fields)), 'unsupported_operands': unsupported}
