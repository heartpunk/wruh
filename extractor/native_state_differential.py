"""Compare captured integer and memory state for one instruction.

Only a restricted subset is currently classifiable. Anything outside it raises
an explicit incomplete result; this module does not silently skip instructions.
"""
from __future__ import annotations

from typing import Any

import iced_x86 as ice
import z3
from z3.z3util import get_vars

from extractor.concrete_instruction import IncompleteEvaluation, evaluate_instruction
from extractor.native_memory_scope import memory_accesses
from extractor.native_state_compare import ConcreteState, StateDomain
from extractor.native_step import REGISTERS, _extra_pages

_FLAG_BITS = {'CF': 0, 'PF': 2, 'AF': 4, 'ZF': 6, 'SF': 7, 'OF': 11}
_FLAG_MASK = sum(1 << bit for bit in _FLAG_BITS.values())


def compare_native_state(model: Any, capture: dict, initial_memory: bytes) -> dict:
    """Compare mapped integer and memory state; reject unmapped effects."""
    from extractor.amd64_state import (
        canonical_declarations,
        canonical_flag,
        canonical_memory,
        canonical_register,
    )

    try:
        before, after = capture['before'], capture['after']
        normal_stop = capture['signal'] == 5 and capture['signal_code'] == 2
        divide_fault = capture['signal'] == 8 and capture['signal_code'] in (1, 2)
        if not normal_stop and not divide_fault:
            raise IncompleteEvaluation(f"native stop signal={capture['signal']} code={capture['signal_code']} is not yet classified")
        addresses = {name: before[name] for name in REGISTERS}
        addresses.update(rip=before['rip'] + len(model.encoded),
                         fs_base=before['fs_base'], gs_base=before['gs_base'])
        extra_pages = _extra_pages(model.encoded, addresses)
        reported = tuple(capture[f'extra{i}_base'] for i in (1, 2) if capture[f'extra{i}_base'])
        if reported != extra_pages:
            raise IncompleteEvaluation('captured extra pages differ from the address plan')
        memory_accesses(model.encoded, addresses, ip=model.source,
                        extra_ranges=tuple((page, page + 4096) for page in extra_pages))
        native_memory = (bytes.fromhex(capture['data']) + bytes.fromhex(capture['stack'])
                         + bytes.fromhex(capture['code'])
                         + b''.join(bytes.fromhex(capture[f'extra{i}']) for i in (1, 2)))
        if len(initial_memory) != 8192 or len(native_memory) != 12288 + 4096 * len(extra_pages):
            raise IncompleteEvaluation('native memory capture is incomplete')
        before_xstate = bytes.fromhex(capture['before_xstate'])
        after_xstate = bytes.fromhex(capture['after_xstate'])
        fxsave = capture.get('xstate_format') == 2 and len(before_xstate) == len(after_xstate) == 512
        if fxsave:
            if before_xstate[:160] + before_xstate[416:] != after_xstate[:160] + after_xstate[416:]:
                raise IncompleteEvaluation('unmapped native floating-point state changed')
        elif before_xstate != after_xstate:
            changed = [i for i, (before_byte, after_byte) in
                       enumerate(zip(before_xstate, after_xstate)) if before_byte != after_byte]
            raise IncompleteEvaluation(
                f'native extended state changed and has no model mapping: '
                f'before_length={len(before_xstate)} after_length={len(after_xstate)} '
                f'changed_count={len(changed)} first_changed_offsets={changed[:64]}'
            )
        stable_fields = ('cs', 'ss', 'ds', 'es', 'fs', 'gs')
        if any(before[name] != after[name] for name in stable_fields):
            return {'status': 'MISMATCH', 'reason': 'native segment state changed'}
        # A divide fault saves RF=1 in the exception-frame flags image;
        # WRUH's six-flag model does not include RF. Compare that architectural
        # exception-delivery effect explicitly instead of discarding the bit.
        # Intel SDM vol. 3B section 19.3.1 and AMD APM vol. 2 section 3.1.6.
        rf_mask = (1 << 16) if divide_fault else 0
        unmapped_flag_changes = (before['eflags'] ^ after['eflags']) & ~(_FLAG_MASK | (1 << 10) | rf_mask)
        if unmapped_flag_changes:
            raise IncompleteEvaluation(f'unmapped native flags changed: {unmapped_flag_changes:#x}')

        declarations = canonical_declarations()
        symbols = {d.name: (canonical_flag(d.name.removeprefix('rflags_'))
                            if d.name.startswith('rflags_') else canonical_register(d.name))
                   for d in declarations if d.name != 'mem'}
        widths = {d.name: d.width for d in declarations if d.name != 'mem'}
        known = set(REGISTERS) | {'rip', 'd', 'fs', 'gs'} | {f'rflags_{name}' for name in _FLAG_BITS}
        if fxsave:
            known.update({f'zmm{i}' for i in range(16)} | {'sseround'})
        initial = {name: 0 for name in widths}
        initial.update({name: before[name] for name in REGISTERS})
        initial['rip'] = before['rip']
        initial['fs'], initial['gs'] = before['fs_base'], before['gs_base']
        initial['d'] = ((1 << widths['d']) - 1) if before['eflags'] & (1 << 10) else 1
        if fxsave:
            initial['sseround'] = (int.from_bytes(before_xstate[24:28], 'little') >> 13) & 3
            for index in range(16):
                initial[f'zmm{index}'] = int.from_bytes(before_xstate[160 + 16 * index:176 + 16 * index], 'little')
        initial.update({f'rflags_{name}': (before['eflags'] >> bit) & 1
                        for name, bit in _FLAG_BITS.items()})
        for outcome in model.relation.outcomes:
            if set(outcome.updates) - known - {'mem'}:
                raise IncompleteEvaluation('model changes an unmapped state field')
            expressions = [outcome.guard, *outcome.updates.values()]
            dependencies = {str(variable) for expr in expressions for variable in get_vars(expr)}
            if dependencies - known - {'mem'}:
                raise IncompleteEvaluation(f'model reads unmapped state: {sorted(dependencies - known - {"mem"})}')
        memory_addresses = (tuple(range(0x100000, 0x101000)) + tuple(range(0x200000, 0x201000))
                            + tuple(range(0x400000, 0x401000))
                            + tuple(address for page in extra_pages for address in range(page, page + 4096)))
        code_memory = model.encoded + bytes(4096 - len(model.encoded))
        memory = dict(zip(memory_addresses, initial_memory + code_memory + bytes(4096 * len(extra_pages))))
        state = ConcreteState(initial, memory)
        result = evaluate_instruction(model.relation, symbols, canonical_memory(), state,
                                      StateDomain(widths, frozenset(memory_addresses)))
        differences = {name: (after[name], result.state.registers[name])
                       for name in (*REGISTERS, 'rip') if after[name] != result.state.registers[name]}
        differences.update({f'rflags_{name}': ((after['eflags'] >> bit) & 1,
                                              result.state.registers[f'rflags_{name}'])
                            for name, bit in _FLAG_BITS.items()
                            if ((after['eflags'] >> bit) & 1) != result.state.registers[f'rflags_{name}']})
        instruction = ice.Decoder(64, model.encoded, ip=model.source).decode()
        undefined = ([] if divide_fault else [name for name in _FLAG_BITS
                     if instruction.rflags_undefined & getattr(ice.RflagsBits, name)])
        if divide_fault and (not after['eflags'] & (1 << 16)):
            differences['rflags_RF'] = (0, 1)
        model_divide_fault = result.jumpkind == 'Ijk_SigFPE_IntDiv'
        if divide_fault != model_divide_fault:
            differences['termination'] = ('divide fault' if divide_fault else 'single step', result.jumpkind)
        undefined_differences = {f'rflags_{name}': differences.pop(f'rflags_{name}')
                                 for name in undefined if f'rflags_{name}' in differences}
        for name in ('fs', 'gs'):
            native_base = after[name + '_base']
            if native_base != result.state.registers[name]:
                differences[name] = (native_base, result.state.registers[name])
        if fxsave:
            for index in range(16):
                name = f'zmm{index}'
                value = result.state.registers[name]
                if value >> 128:
                    raise IncompleteEvaluation(f'model changes unobservable upper bits of {name}')
                native_value = int.from_bytes(after_xstate[160 + 16 * index:176 + 16 * index], 'little')
                if native_value != value:
                    differences[name] = (native_value, value)
            native_round = (int.from_bytes(after_xstate[24:28], 'little') >> 13) & 3
            if native_round != result.state.registers['sseround']:
                differences['sseround'] = (native_round, result.state.registers['sseround'])
        native_direction = ((1 << widths['d']) - 1) if after['eflags'] & (1 << 10) else 1
        if native_direction != result.state.registers['d']:
            differences['d'] = (native_direction, result.state.registers['d'])
        mismatching_memory = [(addr, native, result.state.memory[addr])
                              for addr, native in zip(memory_addresses, native_memory)
                              if native != result.state.memory[addr]]
        if mismatching_memory:
            differences['memory'] = mismatching_memory
        # Undefined outputs have no required architectural value; do not
        # compare them, and report them explicitly alongside the result.
        status = 'MISMATCH' if differences else 'MATCH'
        result_data = {'status': status, 'differences': differences, 'undefined_flags': undefined,
                       'undefined_differences': undefined_differences,
                       'jumpkind': result.jumpkind, 'outcome_id': result.outcome_id}
        return result_data
    except (IncompleteEvaluation, KeyError, TypeError, ValueError, z3.Z3Exception) as exc:
        return {'status': 'INCOMPLETE', 'reason': f'{type(exc).__name__}: {exc}'}
