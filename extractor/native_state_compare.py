"""Strict comparison of concrete states produced by native and model runners.

Both runners must agree on the complete observed register and memory domains.
A caller must declare that domain explicitly; partial capture is incomplete,
not a successful differential comparison.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class ConcreteState:
    registers: Mapping[str, int]
    memory: Mapping[int, int]


@dataclass(frozen=True)
class StateDomain:
    registers: Mapping[str, int]
    memory_addresses: frozenset[int]

    def __post_init__(self) -> None:
        if not self.registers or any(
            not isinstance(name, str) or not name or type(width) is not int or width <= 0
            for name, width in self.registers.items()
        ):
            raise ValueError('register names and positive bit widths are required')
        if any(type(addr) is not int or not 0 <= addr < 2**64 for addr in self.memory_addresses):
            raise ValueError('memory addresses must be unsigned 64-bit integers')


def _validate(state: ConcreteState, domain: StateDomain) -> None:
    if set(state.registers) != set(domain.registers):
        raise ValueError('register domain differs from declared domain')
    if set(state.memory) != domain.memory_addresses:
        raise ValueError('memory domain differs from declared domain')
    for name, width in domain.registers.items():
        value = state.registers[name]
        if type(value) is not int or not 0 <= value < 2**width:
            raise ValueError(f'invalid value for register {name}')
    if any(type(value) is not int or not 0 <= value < 256 for value in state.memory.values()):
        raise ValueError('memory values must be bytes')


def compare_states(native: ConcreteState, model: ConcreteState, domain: StateDomain) -> dict:
    """Compare every declared bit and byte; reject either incomplete state."""
    _validate(native, domain)
    _validate(model, domain)
    registers = {name: (native.registers[name], model.registers[name])
                 for name in sorted(domain.registers)
                 if native.registers[name] != model.registers[name]}
    memory = {addr: (native.memory[addr], model.memory[addr])
              for addr in sorted(domain.memory_addresses)
              if native.memory[addr] != model.memory[addr]}
    return {'status': 'MISMATCH' if registers or memory else 'MATCH',
            'registers': registers, 'memory': memory}
