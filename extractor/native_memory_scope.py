"""Check iced's concrete memory accesses against the runner's mapped pages.

An unclassifiable or out-of-range access is an explicit incomplete case, never
permission to execute with an unobserved memory domain.
"""
from __future__ import annotations

import iced_x86 as ice


class MemoryScopeError(ValueError):
    pass


_NAMES = {value: name.lower() for name, value in vars(ice.Register).items()
          if name.isupper() and isinstance(value, int)}
_RANGES = ((0x100000, 0x101000), (0x200000, 0x201000))
_CODE_RANGE = (0x400000, 0x401000)


def memory_accesses(encoded: bytes, registers: dict[str, int], *, ip: int = 0x400000,
                    extra_ranges: tuple[tuple[int, int], ...] = (),
                    permit_unmapped: bool = False) -> tuple[tuple[int, int], ...]:
    decoder = ice.Decoder(64, encoded, ip=ip)
    ins = decoder.decode()
    if ins.is_invalid or ins.len != len(encoded):
        raise MemoryScopeError('invalid instruction encoding')
    if ins.has_rep_prefix or ins.has_repne_prefix:
        raise MemoryScopeError('repeated instructions require multi-access memory modeling')
    if ins.mnemonic == ice.Mnemonic.ENTER:
        raise MemoryScopeError('ENTER requires multi-access memory modeling')
    accesses = []

    def read_register(reg: int) -> int:
        if reg == ice.Register.NONE:
            return 0
        name = _NAMES.get(ice.RegisterExt.full_register(reg))
        if name not in registers:
            raise MemoryScopeError(f'missing address register {name}')
        size = ice.RegisterExt.size(reg)
        if size not in (2, 4, 8):
            raise MemoryScopeError('unsupported address-register width')
        return registers[name] & ((1 << (8 * size)) - 1)

    for mem in ice.InstructionInfoFactory().info(ins).used_memory():
        if mem.vsib_size:
            raise MemoryScopeError('vector-indexed memory is not yet supported')
        width = ice.MemorySizeExt.size(mem.memory_size)
        if width <= 0:
            raise MemoryScopeError('unknown memory access width')
        if mem.segment in (ice.Register.FS, ice.Register.GS):
            segment = _NAMES[mem.segment] + '_base'
            if segment not in registers:
                raise MemoryScopeError(f'missing {segment}')
            segment_base = registers[segment]
        elif mem.segment in (ice.Register.NONE, ice.Register.CS, ice.Register.DS,
                             ice.Register.ES, ice.Register.SS):
            segment_base = 0
        else:
            raise MemoryScopeError('unknown segment')
        address_bits = {ice.CodeSize.CODE16: 16, ice.CodeSize.CODE32: 32,
                        ice.CodeSize.CODE64: 64}.get(mem.address_size)
        if address_bits is None:
            raise MemoryScopeError('unknown address width')
        offset = (read_register(mem.base) + read_register(mem.index) * mem.scale + mem.displacement)
        address = (segment_base + (offset & ((1 << address_bits) - 1))) & ((1 << 64) - 1)
        allowed = [*_RANGES, *extra_ranges]
        if mem.access in (ice.OpAccess.READ, ice.OpAccess.COND_READ):
            allowed.append(_CODE_RANGE)
        # An access may span adjacent mapped pages, but never a gap.
        cursor = address
        for start, end in sorted(allowed):
            if start <= cursor < end:
                cursor = min(address + width, end)
                if cursor == address + width:
                    break
        if cursor != address + width and not permit_unmapped:
            raise MemoryScopeError(f'access {address:#x}+{width} outside permitted observed pages')
        accesses.append((address, width))
    return tuple(accesses)
