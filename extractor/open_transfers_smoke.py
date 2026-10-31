"""Extract real AMD64 open transfers from a compiler-free ELF fixture.

The tiny ELF contains instruction bytes and ordinary sized function symbols;
CLE, inventory, CFG recovery and fresh extraction all run without mocks. The
fixture is loaded as data and is never executed natively.
"""
from extractor.runtime_trace import start_runtime_trace

start_runtime_trace()
from extractor.native_runtime import preload_libstdcxx

preload_libstdcxx()

import argparse
import hashlib
import json
import struct
import tempfile
from dataclasses import replace
from pathlib import Path

import z3
from ayxg.expr import TermSort, TypedExpr
from ayxg.z3 import declaration_variables, expr_to_z3

from extractor.artifact import Target
from extractor.binary_cfg import build_static_cfg
from extractor.binary_inventory import (
    exact_symbol_inventory_policy,
    inventory,
    load_pinned_binary,
)
from extractor.fresh import FreshFunction, extract_fresh_function

BASE = 0x400000
TEXT_OFFSET = 0x1000
EXTERNAL = 0x70000000
# Calls have ordinary in-range continuations; this does not exercise the
# separate policy question of calls at the very end of a symbol extent.
# Call addresses also force a carry when computing their return addresses,
# distinguishing addition from bitwise OR/XOR in the independent oracle.
FIXTURES = (
    ('direct_call', 3, b'\xe8' + struct.pack('<i', EXTERNAL - (BASE + TEXT_OFFSET + 3 + 5)) + b'\xc3', True, False),
    ('indirect_call', 18, b'\xff\xd0\xc3', True, True),  # call rax; ret
    ('direct_tail', 32, b'\xe9' + struct.pack('<i', EXTERNAL - (BASE + TEXT_OFFSET + 32 + 5)), False, False),
    ('indirect_tail', 48, b'\xff\xe0', False, True),  # jmp rax
)


# An independent contract for this pinned AMD64 runtime, deliberately not read
# from the extractor's architecture/declaration helpers or extracted output.
AMD64_SORTS = {
    **dict.fromkeys([
        'rax', 'rcx', 'rdx', 'rbx', 'rsp', 'rbp', 'rsi', 'rdi',
        'r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15',
        'd', 'rip', 'ac', 'id', 'fs', 'sseround', 'cr0', 'cr2', 'cr3', 'cr4', 'cr8',
        'fptag', 'fpround', 'fc3210', 'cmstart', 'cmlen', 'nraddr', 'gs', 'ip_at_syscall',
    ], TermSort.bv(64)),
    **{f'zmm{index}': TermSort.bv(512) for index in range(32)},
    **{f'k{index}': TermSort.bv(64) for index in range(8)},
    'ftop': TermSort.bv(32), 'emnote': TermSort.bv(32), 'fpreg': TermSort.bv(512),
    **{f'{segment}_seg': TermSort.bv(16) for segment in ('cs', 'ds', 'es', 'fs', 'gs', 'ss')},
    **{f'rflags_{flag}': TermSort.bv(1) for flag in ('CF', 'ZF', 'SF', 'OF', 'PF', 'AF')},
    'mem': TermSort.array(64, 8),
}


def write_fixture(path):
    """Write ELF64 headers, one RX segment, .text and a real symbol table.

    Encoding the fixed bytes directly avoids a compiler/linker dependency in
    the existing Python smoke command. No inventory or CFG data is supplied.
    """
    text = bytearray(b'\x90' * 50)
    strings = bytearray(b'\0')
    symbols = bytearray(24)  # required null symbol
    for name, offset, code, _, _ in FIXTURES:
        text[offset:offset + len(code)] = code
        name_offset = len(strings)
        strings.extend(name.encode() + b'\0')
        symbols.extend(struct.pack('<IBBHQQ', name_offset, 0x12, 0, 1,
                                   BASE + TEXT_OFFSET + offset, len(code)))
    section_names = b'\0.text\0.symtab\0.strtab\0.shstrtab\0'
    sym_offset = (TEXT_OFFSET + len(text) + 7) & ~7
    str_offset = sym_offset + len(symbols)
    names_offset = str_offset + len(strings)
    sections_offset = (names_offset + len(section_names) + 7) & ~7
    raw = bytearray(sections_offset + 5 * 64)
    ident = b'\x7fELF\x02\x01\x01' + bytes(9)
    raw[:64] = struct.pack('<16sHHIQQQIHHHHHH', ident, 2, 62, 1,
                          BASE + TEXT_OFFSET, 64, sections_offset, 0,
                          64, 56, 1, 64, 5, 4)
    raw[64:120] = struct.pack('<IIQQQQQQ', 1, 5, 0, BASE, BASE,
                             TEXT_OFFSET + len(text), TEXT_OFFSET + len(text), 0x1000)
    raw[TEXT_OFFSET:TEXT_OFFSET + len(text)] = text
    raw[sym_offset:sym_offset + len(symbols)] = symbols
    raw[str_offset:str_offset + len(strings)] = strings
    raw[names_offset:names_offset + len(section_names)] = section_names
    sections = (
        (1, 1, 6, BASE + TEXT_OFFSET, TEXT_OFFSET, len(text), 0, 0, 16, 0),
        (7, 2, 0, 0, sym_offset, len(symbols), 3, 1, 8, 24),
        (15, 3, 0, 0, str_offset, len(strings), 0, 0, 1, 0),
        (23, 3, 0, 0, names_offset, len(section_names), 0, 0, 1, 0),
    )
    for index, section in enumerate(sections, 1):
        start = sections_offset + index * 64
        raw[start:start + 64] = struct.pack('<IIQQQQIIQQ', *section)
    path.write_bytes(raw)


def complete_solver_result(solver):
    result = solver.check()
    if result == z3.unknown:
        raise RuntimeError('INCOMPLETE: ' + solver.reason_unknown())
    return result


def check_unknown_control():
    # Force resource exhaustion deterministically, without waiting for timeout
    # or replacing the real solver. Incomplete work must escape rejection's
    # AssertionError handler, never count as a semantic counterexample.
    solver = z3.Solver()
    solver.set(rlimit=1, timeout=5000)
    value = z3.Int('unknown_control')
    solver.add(value * value == 2)
    try:
        complete_solver_result(solver)
    except RuntimeError as error:
        assert str(error).startswith('INCOMPLETE: ')
        return
    raise AssertionError('resource-limited control did not report INCOMPLETE')


def check_transfer(function, name, address, code, is_call, symbolic):
    # Check the serialized consumer representation, not Python-only state.
    function = FreshFunction.from_data(json.loads(function.canonical_json()))
    assert len(function.declarations) == 91, (name, 'declaration count')
    assert {item.name: item.sort for item in function.declarations} == AMD64_SORTS, (name, 'AMD64 state contract')
    occurrence = next(item for item in function.occurrences
                      if item.origin.canonical_address == address)
    assert occurrence.origin.instruction_bytes == code[:2 if symbolic else 5].hex(), name
    edges = [edge for edge in function.local_edges if edge.source == address]
    assert len(edges) == 1, (name, len(edges))
    summary = edges[0].summary
    assert summary.external_effect is None, name
    ctx = z3.Context()
    variables = declaration_variables(function.declarations, ctx)
    actual = {assignment.name: expr_to_z3(assignment.value, variables, ctx)
              for assignment in summary.simultaneous_update}
    assert set(actual) == set(variables), name
    expected = dict(variables)
    target = variables['rax'] if symbolic else z3.BitVecVal(EXTERNAL, 64, ctx=ctx)
    expected['rip'] = target
    if is_call:
        expected['rsp'] = variables['rsp'] - 8
        memory = variables['mem']
        return_address = address + (2 if symbolic else 5)
        for index in range(8):
            memory = z3.Store(memory, expected['rsp'] + index,
                              z3.BitVecVal((return_address >> (8 * index)) & 255, 8, ctx=ctx))
        expected['mem'] = memory
    guard = expr_to_z3(summary.guard, variables, ctx)
    expected_guard = variables['rip'] == address

    def unsat(condition, label):
        solver = z3.Solver(ctx=ctx)
        solver.set(timeout=5000)
        solver.add(condition)
        assert complete_solver_result(solver) == z3.unsat, (name, label, solver)

    unsat(z3.Xor(guard, expected_guard), 'exact source guard')
    for variable in variables:
        unsat(z3.And(guard, actual[variable] != expected[variable]),
              'full poststate: ' + variable)
    assert summary.target.kind == ('symbolic' if symbolic else 'address'), name
    if symbolic:
        unsat(expr_to_z3(summary.target.value, variables, ctx) != target,
              'symbolic target retained')
    else:
        assert summary.target.value == EXTERNAL, name
    unsat(expr_to_z3(summary.mirrored_pc, variables, ctx) != target, 'mirrored PC')
    # Explicit witnesses prevent vacuous UNSAT checks and constrain the target
    # outside the loaded image: no return from that boundary is synthesized.
    solver = z3.Solver(ctx=ctx)
    solver.set(timeout=5000)
    solver.add(guard, variables['rsp'] == 0x800008, variables['rax'] == EXTERNAL)
    assert complete_solver_result(solver) == z3.sat, (name, 'reachable open transfer')
    model = solver.model()
    assert model.eval(actual['rip']).as_long() == EXTERNAL, name
    assert model.eval(actual['rsp']).as_long() == (0x800000 if is_call else 0x800008), name
    return {'declarations_checked': len(variables),
            'instruction_bytes': occurrence.origin.instruction_bytes,
            'guard': 'exact source PC (UNSAT)', 'poststate': 'all declarations (UNSAT)',
            'witness': 'SAT', 'target': 'rax' if symbolic else EXTERNAL,
            'stack': 'push exact return address' if is_call else 'preserved'}


def check_rejection_controls(function, fixture):
    """Small corruptions of real extracted output must fail the same oracle."""
    name, offset, code, is_call, symbolic = fixture
    address = BASE + TEXT_OFFSET + offset
    edge = next(item for item in function.local_edges if item.source == address)
    summary = edge.summary

    def changed_summary(**fields):
        changed = replace(edge, summary=replace(summary, **fields))
        return replace(function, local_edges=tuple(
            changed if item == edge else item for item in function.local_edges))

    def changed_assignment(variable, value):
        return changed_summary(simultaneous_update=tuple(
            replace(item, value=value) if item.name == variable else item
            for item in summary.simultaneous_update))

    missing_rbx = changed_summary(simultaneous_update=tuple(
        item for item in summary.simultaneous_update if item.name != 'rbx'))
    missing_rbx = replace(missing_rbx, declarations=tuple(
        item for item in function.declarations if item.name != 'rbx'))
    corruptions = {
        'missing rbx and assignment': missing_rbx,
        'guard': changed_summary(guard=TypedExpr.equal(
            TypedExpr.var('rip', TermSort.bv(64)), TypedExpr.bv_lit(64, address + 1))),
        'memory': changed_assignment('mem', TypedExpr.var('mem', TermSort.array(64, 8))),
        'preserved register': changed_assignment('rbx', TypedExpr.bv_lit(64, 0)),
        'target': changed_summary(target=Target('address', EXTERNAL + 1)),
    }
    for label, corrupted in corruptions.items():
        try:
            check_transfer(corrupted, name, address, code, is_call, symbolic)
        except AssertionError:
            continue
        raise AssertionError(f'oracle accepted corrupted {label}')
    return list(corruptions)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    assert tuple((name, is_call, symbolic) for name, _, _, is_call, symbolic in FIXTURES) == (
        ('direct_call', True, False), ('indirect_call', True, True),
        ('direct_tail', False, False), ('indirect_tail', False, True),
    ), 'fixed four-case transfer roster'
    check_unknown_control()
    roots = tuple(item[0] for item in FIXTURES)
    with tempfile.TemporaryDirectory() as temp:
        artifact = Path(temp) / 'open-transfers.elf'
        manifest_path = Path(temp) / 'inventory.json'
        write_fixture(artifact)
        policy = exact_symbol_inventory_policy(roots, open_transfers=True,
                                               discover_direct_targets=False)
        manifest = inventory(artifact, policy)
        manifest_path.write_text(json.dumps(manifest))
        pinned = load_pinned_binary(artifact, manifest_path, policy)
        assert not pinned.project.loader.find_object_containing(EXTERNAL)
        cfg = build_static_cfg(pinned)
        assert set(cfg['roots']) == set(roots)
        results = {}
        rejection_controls = None
        for name, offset, code, is_call, symbolic in FIXTURES:
            address = BASE + TEXT_OFFSET + offset
            if is_call:
                calls = cfg['roots'][name]['calls']
                assert len(calls) == 1 and calls[0]['kind'] == 'open', name
                assert calls[0]['target'] == (None if symbolic else EXTERNAL), name
                instructions = [instruction for block in cfg['roots'][name]['blocks']
                                for instruction in block['instructions']]
                assert any(item['address'] == address + len(code) - 1
                           and item['mnemonic'] == 'ret' for item in instructions), name
            function = extract_fresh_function(pinned, cfg, name)
            assert all(item.origin.image_sha256 == manifest['image_sha256']
                       for item in function.occurrences)
            results[name] = check_transfer(function, name, address, code, is_call, symbolic)
            if name == 'direct_call':
                rejection_controls = check_rejection_controls(function, (name, offset, code, is_call, symbolic))
        result = {'pipeline': 'ELF / pinned inventory / CFG / fresh extraction / JSON roundtrip',
                  'image_sha256': hashlib.sha256(artifact.read_bytes()).hexdigest(),
                  'native_execution': False, 'transfers': results,
                  'rejection_controls': rejection_controls}
    rendered = json.dumps(result, sort_keys=True) + '\n'
    if args.output:
        args.output.write_text(rendered)
    print(rendered, end='')


if __name__ == '__main__':
    main()
