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
from pathlib import Path

import z3
from ayxg.z3 import declaration_variables, expr_to_z3

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
FIXTURES = (
    ('direct_call', 0, b'\xe8' + struct.pack('<i', EXTERNAL - (BASE + TEXT_OFFSET + 5)) + b'\xc3', True, False),
    ('indirect_call', 16, b'\xff\xd0\xc3', True, True),  # call rax; ret
    ('direct_tail', 32, b'\xe9' + struct.pack('<i', EXTERNAL - (BASE + TEXT_OFFSET + 32 + 5)), False, False),
    ('indirect_tail', 48, b'\xff\xe0', False, True),  # jmp rax
)


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


def check_transfer(function, name, address, code, is_call, symbolic):
    # Check the serialized consumer representation, not Python-only state.
    function = FreshFunction.from_data(json.loads(function.canonical_json()))
    assert function.canonical_json() == FreshFunction.from_data(function.to_data()).canonical_json()
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
        solver.add(condition)
        assert solver.check() == z3.unsat, (name, label, solver)

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
    solver.add(guard, variables['rsp'] == 0x800008, variables['rax'] == EXTERNAL)
    assert solver.check() == z3.sat, (name, 'reachable open transfer')
    model = solver.model()
    assert model.eval(actual['rip']).as_long() == EXTERNAL, name
    assert model.eval(actual['rsp']).as_long() == (0x800000 if is_call else 0x800008), name
    return {'declarations_checked': len(variables),
            'instruction_bytes': occurrence.origin.instruction_bytes,
            'guard': 'exact source PC (UNSAT)', 'poststate': 'all declarations (UNSAT)',
            'witness': 'SAT', 'target': 'rax' if symbolic else EXTERNAL,
            'stack': 'push exact return address' if is_call else 'preserved'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
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
        result = {'pipeline': 'ELF / pinned inventory / CFG / fresh extraction / JSON roundtrip',
                  'image_sha256': hashlib.sha256(artifact.read_bytes()).hexdigest(),
                  'native_execution': False, 'transfers': results}
    rendered = json.dumps(result, sort_keys=True) + '\n'
    if args.output:
        args.output.write_text(rendered)
    print(rendered, end='')


if __name__ == '__main__':
    main()
