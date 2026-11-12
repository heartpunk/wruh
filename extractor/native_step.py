"""Validate and capture one native instruction in the bubblewrap runner."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from extractor.isolated_native import NativeIsolationError, run_isolated
from extractor.native_memory_scope import MemoryScopeError, memory_accesses

REGISTERS = ('rax', 'rbx', 'rcx', 'rdx', 'rsi', 'rdi', 'rbp', 'rsp',
             'r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15')


def _extra_pages(encoded: bytes, registers: dict[str, int]) -> tuple[int, ...]:
    accesses = memory_accesses(encoded, registers, permit_unmapped=True)
    fixed = {0x100000, 0x200000, 0x400000}
    pages = set()
    for address, width in accesses:
        if address + width > 2**64:
            raise MemoryScopeError('memory access wraps the address space')
        for page in range(address & ~4095, ((address + width - 1) & ~4095) + 1, 4096):
            if page not in fixed:
                if page < 0x10000 or page > 0x00007ffffffff000:
                    raise MemoryScopeError(f'extra page {page:#x} is outside the permitted user range')
                pages.add(page)
    if len(pages) > 2:
        raise MemoryScopeError(f'{len(pages)} extra pages exceed the two-page bound')
    return tuple(sorted(pages))


def capture_step(bwrap: Path, runner: Path, runtime: tuple[Path, ...],
                 encoded: bytes, registers: dict[str, int], flags: int,
                 memory: bytes, *, fs_base: int = 0, gs_base: int = 0,
                 xmm: bytes = bytes(256)) -> dict[str, Any]:
    """Return raw capture; callers must still map and compare full state."""
    if not isinstance(encoded, bytes) or not 1 <= len(encoded) <= 15:
        raise NativeIsolationError('instruction encoding must contain one to fifteen bytes')
    if set(registers) != set(REGISTERS):
        raise NativeIsolationError('all sixteen general registers are required')
    if any(type(v) is not int or not 0 <= v < 2**64 for v in registers.values()):
        raise NativeIsolationError('register values must be unsigned 64-bit integers')
    if type(flags) is not int or flags < 0 or flags & ~0xcd5:
        raise NativeIsolationError('unsupported initial flags')
    if any(type(value) is not int or not 0 <= value < 2**64 for value in (fs_base, gs_base)):
        raise NativeIsolationError('FS/GS bases must be unsigned 64-bit integers')
    if not isinstance(xmm, bytes) or len(xmm) != 256:
        raise NativeIsolationError('sixteen complete XMM registers are required')
    if not isinstance(memory, bytes) or len(memory) != 8192:
        raise NativeIsolationError('two complete 4096-byte memory pages are required')
    address_state = {**registers, 'rip': 0x400000 + len(encoded),
                     'fs_base': fs_base, 'gs_base': gs_base}
    extra_pages = _extra_pages(encoded, address_state)
    memory_accesses(encoded, address_state,
                    extra_ranges=tuple((page, page + 4096) for page in extra_pages))
    bases = (*extra_pages, *(0 for _ in range(2 - len(extra_pages))))
    response = run_isolated(bwrap, runner, runtime,
                            {'bytes': encoded.hex(), 'memory': memory.hex(), 'xmm': xmm.hex(),
                             'extra1_base': bases[0], 'extra2_base': bases[1],
                             'registers': {**registers, 'eflags': flags,
                                           'fs_base': fs_base, 'gs_base': gs_base}})
    try:
        before, after = response['before'], response['after']
        if any(before[name] != value for name, value in registers.items()):
            raise NativeIsolationError('native pre-state differs from requested registers')
        if (before['rip'] != 0x400000 or (before['eflags'] & 0xcd5) != flags
                or before['fs_base'] != fs_base or before['gs_base'] != gs_base):
            raise NativeIsolationError('native pre-state differs from requested RIP or flags')
        if type(response['signal']) is not int or type(response['signal_code']) is not int:
            raise NativeIsolationError('native stop lacks signal information')
        if response['xstate_format'] not in (1, 2):
            raise NativeIsolationError('unsupported native extended-state format')
        before_xstate = bytes.fromhex(response['before_xstate'])
        after_xstate = bytes.fromhex(response['after_xstate'])
        if before_xstate[160:416] != xmm:
            raise NativeIsolationError('native XMM pre-state differs from the request')
        if (len(before_xstate) != len(after_xstate) or len(before_xstate) < 512
                or (response['xstate_format'] == 2 and len(before_xstate) != 512)):
            raise NativeIsolationError('invalid extended-state capture')
        if len(bytes.fromhex(response['data'])) != 4096 or len(bytes.fromhex(response['stack'])) != 4096:
            raise NativeIsolationError('invalid memory capture')
        for index, base in enumerate(bases, 1):
            if response[f'extra{index}_base'] != base or len(bytes.fromhex(response[f'extra{index}'])) != (4096 if base else 0):
                raise NativeIsolationError('invalid extra-page capture')
        if bytes.fromhex(response['code']) != encoded + bytes(4096 - len(encoded)):
            raise NativeIsolationError('code page capture differs from the requested encoding')
        if any(name not in after for name in (*REGISTERS, 'rip', 'eflags')):
            raise NativeIsolationError('native post-state is incomplete')
    except (KeyError, TypeError, ValueError) as exc:
        raise NativeIsolationError(f'invalid native capture: {exc}') from exc
    return response
