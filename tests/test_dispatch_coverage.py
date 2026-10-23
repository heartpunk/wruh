"""Real ELF dispatch discovery; table seeds never restrict symbolic jumps."""
from extractor.runtime_trace import start_runtime_trace

start_runtime_trace()
from extractor.native_runtime import preload_libstdcxx

preload_libstdcxx()

import json
import struct
import tempfile
from dataclasses import replace
from pathlib import Path

import z3
from ayxg.expr import TermSort, TypedExpr
from ayxg.z3 import declaration_variables, expr_to_z3

from extractor.binary_cfg import build_static_cfg
from extractor.binary_inventory import (
    exact_symbol_inventory_policy,
    inventory,
    load_pinned_binary,
)
from extractor.fresh import FreshExtractionError, FreshFunction, extract_fresh_function
from extractor.open_transfers_smoke import AMD64_SORTS, complete_solver_result

BASE = 0x400000
ENTRY = BASE + 0x1000
EXTERNAL = 0x70000000


def write_fixture(path, relative=False, sized=True, shared=False, table_before=False, prefixed=False):
    table_offset = 0x800 if table_before else 0x1100
    table = BASE + table_offset
    lea = b'\x48\x8d\x15' + struct.pack('<i', table - (ENTRY + 7))
    dispatch = (b'\x48\x63\x04\xba\x48\x01\xd0\xff\xe0' if relative else b'\xff\x24\xfa')
    if prefixed:
        dispatch = b"\x3e" + dispatch
    prefix = lea + dispatch
    first = ENTRY + len(prefix)
    second = first + (1 if shared else 6)
    code = prefix + b'\xb8\x11\x00\x00\x00\xc3\xb8\x22\x00\x00\x00\xc3'
    if shared:
        code = prefix + b'\x90\xb8\x22\x00\x00\x00\xc3'
    targets = [first, EXTERNAL, second, first]
    data = b''.join(struct.pack('<i' if relative else '<Q', target - table if relative else target) for target in targets)
    strings = b'\0dispatch\0dispatch_table\0'
    symbols = bytes(24) + struct.pack('<IBBHQQ', 1, 0x12, 0, 1, ENTRY, len(code))
    symbols += struct.pack('<IBBHQQ', 10, 0x11, 0, 2, table, len(data) if sized else 0)
    names = b'\0.text\0.rodata\0.symtab\0.strtab\0.shstrtab\0'
    symoff = 0x1200
    stroff = symoff + len(symbols)
    nameoff = stroff + len(strings)
    shoff = (nameoff + len(names) + 7) & ~7
    raw = bytearray(shoff + 6 * 64)
    raw[:64] = struct.pack('<16sHHIQQQIHHHHHH', b'\x7fELF\x02\x01\x01' + bytes(9), 2, 62, 1, ENTRY, 64, shoff, 0, 64, 56, 1, 64, 6, 5)
    raw[64:120] = struct.pack('<IIQQQQQQ', 1, 5, 0, BASE, BASE, 0x1100 + len(data), 0x1100 + len(data), 0x1000)
    raw[0x1000:0x1000 + len(code)] = code
    raw[table_offset:table_offset + len(data)] = data
    raw[symoff:symoff + len(symbols)] = symbols
    raw[stroff:stroff + len(strings)] = strings
    raw[nameoff:nameoff + len(names)] = names
    sections = [(1, 1, 6, ENTRY, 0x1000, len(code), 0, 0, 16, 0), (7, 1, 2, table, table_offset, len(data), 0, 0, 8, 0), (15, 2, 0, 0, symoff, len(symbols), 4, 1, 8, 24), (23, 3, 0, 0, stroff, len(strings), 0, 0, 1, 0), (31, 3, 0, 0, nameoff, len(names), 0, 0, 1, 0)]
    for index, section in enumerate(sections, 1):
        raw[shoff + index * 64:shoff + (index + 1) * 64] = struct.pack('<IIQQQQIIQQ', *section)
    path.write_bytes(raw)
    sizes = [7, 4, 3, 2, 5, 1, 5, 1] if relative else [7, 3, 5, 1, 5, 1]
    if prefixed:
        sizes[1] += 1
    if shared:
        sizes = sizes[:-4] + [1, 5, 1]
    return code, sizes, first, second


def check_roster(function, code, sizes):
    actual = [(item.origin.canonical_address, item.origin.instruction_bytes)
              for item in function.occurrences]
    expected = []
    cursor = 0
    for size in sizes:
        expected.append((ENTRY + cursor, code[cursor:cursor + size].hex()))
        cursor += size
    assert actual == expected, ("exact instruction roster", actual, expected)
    assert len(actual) == len(sizes)
    assert {edge.source for edge in function.local_edges} == {address for address, _ in expected}
    assert len(function.local_edges) == len(sizes)


def check_relation(function, address, operation, value=None):
    """Independent full-state oracle for dispatch, loads, and handler instructions."""
    assert {item.name: item.sort for item in function.declarations} == AMD64_SORTS
    edges = [edge for edge in function.local_edges if edge.source == address]
    assert len(edges) == 1
    summary = edges[0].summary
    context = z3.Context()
    variables = declaration_variables(function.declarations, context)
    actual = {item.name: expr_to_z3(item.value, variables, context)
              for item in summary.simultaneous_update}
    assert set(actual) == set(variables)
    expected = dict(variables)

    def word(at, width=8):
        return z3.Concat(*[z3.Select(variables['mem'], at + index)
                           for index in reversed(range(width))])

    if operation == 'absolute':
        target = word(variables['rdx'] + variables['rdi'] * 8)
    elif operation == 'relative':
        target = variables['rax']
    elif operation == 'return':
        target = word(variables['rsp'])
        expected['rsp'] = variables['rsp'] + 8
    elif operation == 'move':
        target = z3.BitVecVal(address + 5, 64, ctx=context)
        expected['rax'] = z3.BitVecVal(value, 64, ctx=context)
    elif operation == 'lea':
        target = z3.BitVecVal(address + 7, 64, ctx=context)
        expected['rdx'] = z3.BitVecVal(ENTRY + 0x100, 64, ctx=context)
    elif operation == 'add':
        target = z3.BitVecVal(address + 3, 64, ctx=context)
        left, right = variables['rax'], variables['rdx']
        result = left + right
        expected['rax'] = result
        bit = lambda condition: z3.If(condition, z3.BitVecVal(1, 1, ctx=context), z3.BitVecVal(0, 1, ctx=context))
        expected['rflags_CF'] = bit(z3.ULT(result, left))
        expected['rflags_ZF'] = bit(result == 0)
        expected['rflags_SF'] = z3.Extract(63, 63, result)
        expected['rflags_OF'] = z3.Extract(63, 63, ~(left ^ right) & (left ^ result))
        expected['rflags_AF'] = z3.Extract(4, 4, left ^ right ^ result)
        parity = z3.Extract(0, 0, result)
        for index in range(1, 8):
            parity = parity ^ z3.Extract(index, index, result)
        expected['rflags_PF'] = ~parity
    elif operation == 'signed-load':
        target = z3.BitVecVal(address + 4, 64, ctx=context)
        expected['rax'] = z3.SignExt(32, word(variables['rdx'] + variables['rdi'] * 4, 4))
    else:
        raise AssertionError(operation)
    expected['rip'] = target
    guard = expr_to_z3(summary.guard, variables, context)

    def prove(condition):
        solver = z3.Solver(ctx=context)
        solver.set(timeout=5000)
        solver.add(condition)
        assert complete_solver_result(solver) == z3.unsat

    prove(z3.Xor(guard, variables['rip'] == address))
    # One disjunction also guards against a mutation skipping per-variable proofs.
    prove(z3.And(guard, z3.Or(*[actual[name] != expected[name] for name in variables])))
    assert summary.external_effect is None
    prove(expr_to_z3(summary.mirrored_pc, variables, context) != target)
    if operation in ('absolute', 'relative', 'return'):
        assert summary.target.kind == 'symbolic'
        prove(expr_to_z3(summary.target.value, variables, context) != target)
    else:
        assert summary.target.kind == 'address' and summary.target.value == address + {'lea': 7, 'signed-load': 4, 'add': 3, 'move': 5}[operation]
    # Each local handler and an out-of-image address must remain feasible.
    witnesses = (value[0], value[1], EXTERNAL) if operation in ('absolute', 'relative') else (None,)
    witnessed = []
    for destination in witnesses:
        solver = z3.Solver(ctx=context)
        solver.set(timeout=5000)
        solver.add(guard)
        if destination is not None:
            solver.add(target == destination)
        assert complete_solver_result(solver) == z3.sat
        if destination is not None:
            assert z3.simplify(solver.model().eval(actual['rip'], model_completion=True)).as_long() == destination
        witnessed.append(destination)
    assert witnessed == list(witnesses)


def check_controls(function, code, sizes, address, operation, destinations):
    edge = next(item for item in function.local_edges if item.source == address)
    corruptions = {
        'guard': replace(edge.summary, guard=TypedExpr.equal(
            TypedExpr.var('rip', TermSort.bv(64)), TypedExpr.bv_lit(64, address + 1))),
        'preserved state': replace(edge.summary, simultaneous_update=tuple(
            replace(item, value=TypedExpr.bv_lit(64, 0)) if item.name == 'rbx' else item
            for item in edge.summary.simultaneous_update)),
    }
    rejected = []
    for label, summary in corruptions.items():
        corrupted = replace(function, local_edges=tuple(
            replace(item, summary=summary) if item == edge else item for item in function.local_edges))
        try:
            check_relation(corrupted, address, operation, destinations)
        except AssertionError:
            rejected.append(label)
        else:
            raise AssertionError('oracle accepted ' + label)
    assert rejected == ['guard', 'preserved state']
    try:
        check_roster(replace(function, occurrences=function.occurrences[:-1]), code, sizes)
    except AssertionError:
        return
    raise AssertionError('oracle accepted missing handler instruction')


def check_coverage_controls(function):
    original = function.to_data()['extraction_coverage']
    cases = [None, {}, {**original, 'status': 'direct-cfg'},
             {**original, 'unresolved_indirect_sites': [ENTRY]},
             {**original, 'unresolved_indirect_sites': [True]},
             {**original, 'status': 'direct-cfg', 'unresolved_indirect_sites': []}]
    rejected = []
    for index, coverage in enumerate(cases):
        data = function.to_data()
        data['extraction_coverage'] = coverage
        try:
            FreshFunction.from_data(data)
        except FreshExtractionError:
            rejected.append(index)
        else:
            raise AssertionError('accepted malformed coverage')
    assert rejected == list(range(len(cases)))


def check_discovery_boundaries():
    cases = ('shared-tail', 'base-is-index', '32-bit-lea', 'interior-target', 'positive-relative', 'prefixed-jump', 'unreadable-table')
    checked = []
    for case in cases:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'boundary.elf'
            code, sizes, first, second = write_fixture(path, shared=case == 'shared-tail', relative=case == 'positive-relative', table_before=case == 'positive-relative', prefixed=case == 'prefixed-jump')
            raw = bytearray(path.read_bytes())
            if case == 'base-is-index':
                raw[0x1009] = 0xd2  # jmp [rdx+rdx*8]: index cannot select each table entry.
            elif case == '32-bit-lea':
                raw[0x1000] = 0x40  # Neutral REX: LEA writes edx, not rdx.
            elif case == 'interior-target':
                raw[0x1110:0x1118] = struct.pack('<Q', second + 1)
            elif case == 'unreadable-table':
                # Two real PT_LOAD mappings with a page-sized hole through the
                # object's table extent. Endpoints belong to the ELF but a full
                # loader-memory read cannot cover the table.
                shoff = struct.unpack_from('<Q', raw, 40)[0]
                symoff = struct.unpack_from('<Q', raw, shoff + 3 * 64 + 24)[0]
                struct.pack_into('<H', raw, 56, 2)
                struct.pack_into('<QQ', raw, 96, 0x1108, 0x1108)
                raw[120:176] = struct.pack('<IIQQQQQQ', 1, 4, 0x3100, BASE + 0x3100, BASE + 0x3100, 8, 8, 0x1000)
                struct.pack_into('<Q', raw, symoff + 48 + 16, 0x2008)
                struct.pack_into('<Q', raw, shoff + 2 * 64 + 32, 0x2008)
                raw.extend(bytes(0x3108 - len(raw)))
                struct.pack_into('<Q', raw, 0x3100, second)
            path.write_bytes(raw)
            policy = exact_symbol_inventory_policy(('dispatch',), open_transfers=True, discover_direct_targets=False)
            manifest = inventory(path, policy)
            manifest_path = path.with_suffix('.json')
            manifest_path.write_text(json.dumps(manifest))
            pinned = load_pinned_binary(path, manifest_path, policy)
            cfg = build_static_cfg(pinned)
            root = cfg['roots']['dispatch']
            assert root['extraction_coverage']['unresolved_indirect_sites'] == [ENTRY + (14 if case == 'positive-relative' else 7)]
            if case == 'positive-relative':
                assert root['blocks'][0]['successors'] == [first, second]
                assert [block['address'] for block in root['blocks']] == [ENTRY, first, second]
                check_roster(extract_fresh_function(pinned, cfg, 'dispatch'), code, sizes)
            elif case == 'shared-tail':
                assert [block['address'] for block in root['blocks']] == [ENTRY, first, second]
                assert root['blocks'][0]['successors'] == [first, second]
                assert root['blocks'][1]['successors'] == [second]
                assert root['blocks'][1]['size'] == 1
                function = extract_fresh_function(pinned, cfg, 'dispatch')
                check_roster(FreshFunction.from_data(json.loads(function.canonical_json())), code, sizes)
            elif case == 'interior-target':
                assert root['blocks'][0]['successors'] == [first]
                assert [block['address'] for block in root['blocks']] == [ENTRY, first]
            elif case == 'prefixed-jump':
                function = extract_fresh_function(pinned, cfg, 'dispatch')
                roundtrip = FreshFunction.from_data(json.loads(function.canonical_json()))
                assert roundtrip.extraction_coverage.unresolved_indirect_sites == (ENTRY + 7,)
            else:
                assert root['blocks'][0]['successors'] == []
                assert len(root['blocks']) == 1
            checked.append(case)
    assert checked == list(cases)


def main():
    checked = []
    for relative in (False, True):
        for sized in (True, False):
            with tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / 'dispatch.elf'
                code, sizes, first, second = write_fixture(path, relative, sized)
                policy = exact_symbol_inventory_policy(('dispatch',), open_transfers=True, discover_direct_targets=False)
                manifest = inventory(path, policy)
                manifest_path = path.with_suffix('.json')
                manifest_path.write_text(json.dumps(manifest))
                pinned = load_pinned_binary(path, manifest_path, policy)
                cfg = build_static_cfg(pinned)
                function = FreshFunction.from_data(json.loads(extract_fresh_function(pinned, cfg, 'dispatch').canonical_json()))
                assert FreshFunction.from_data(json.loads(function.canonical_json())).canonical_json() == function.canonical_json()
                check_coverage_controls(function)
                legacy = function.to_data()
                del legacy['extraction_coverage']
                assert FreshFunction.from_data(legacy).extraction_coverage is None
                dispatch = first - (2 if relative else 3)
                expected_sizes = sizes if sized else sizes[:-4]
                check_roster(function, code, expected_sizes)
                coverage = function.extraction_coverage.to_data()
                assert coverage == {
                    'scope': 'intraprocedural-jumps-only',
                    'status': 'partial-indirect',
                    'unresolved_indirect_sites': [dispatch],
                    'discovery': 'loaded-table-seeds-do-not-bound-symbolic-targets',
                }
                blocks = cfg['roots']['dispatch']['blocks']
                assert blocks[0]['successors'] == ([first, second] if sized else [])
                # Exact, non-overlapping partition; both indirect-only handlers are entries.
                assert [block['address'] for block in blocks] == ([ENTRY, first, second] if sized else [ENTRY])
                operation = 'relative' if relative else 'absolute'
                check_relation(function, dispatch, operation, (first, second))
                check_relation(function, ENTRY, 'lea')
                if relative:
                    check_relation(function, ENTRY + 7, 'signed-load')
                    check_relation(function, ENTRY + 11, 'add')
                if sized:
                    check_relation(function, first, 'move', 0x11)
                    check_relation(function, second, 'move', 0x22)
                    check_relation(function, first + 5, 'return')
                    check_relation(function, second + 5, 'return')
                    check_controls(function, code, sizes, dispatch, operation, (first, second))
                checked.append((relative, sized))
    assert checked == [(False, True), (False, False), (True, True), (True, False)]
    check_discovery_boundaries()
    print('dispatch coverage passed: absolute/relative, sized/unresolved, exact state and corruption controls')


if __name__ == '__main__':
    main()
