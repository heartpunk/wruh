"""Exact external identities through real ELF extraction and artifact links."""
import json
import struct
import tempfile
from dataclasses import replace
from pathlib import Path

from ayxg.expr import ArtifactError, TypedExpr

from extractor.artifact import (
    ContextObservation,
    ContextRun,
    DecodedInstructionEvidence,
    EdgeId,
    ExtractionArtifact,
    FunctionSummary,
    OutcomeId,
    PrefixSummary,
    PrimitiveModelEvidence,
    Root,
    RunEvent,
    StaticOccurrenceId,
    StepSummary,
    SummaryApplication,
    Target,
)

BASE = 0x400000
TEXT_OFFSET = 0x1000

# These are bytes in a real ELF string table, not mocked inventory labels.
# Include spellings that strip/sanitize/Unicode normalization would conflate.
NAMES = ('_Py', 'Py', 'foo.bar', 'foo-bar', 'foo_bar', 'foo@V1', ':lambda',
         ' space\t\n"\\ ', 'é', 'e\u0301', '�')


def check_names(functions):
    from extractor.fresh import FreshFunction

    assert tuple(function.function_id for function in functions) == NAMES
    for index, function in enumerate(functions):
        expected = NAMES[index]
        assert function.entry == BASE + TEXT_OFFSET + index * 16
        assert len(function.occurrences) == (2 if index == 0 else 1)
        for occurrence in function.occurrences:
            assert occurrence.origin.function_owners == (expected,), expected
        restored = FreshFunction.from_data(json.loads(function.canonical_json()))
        assert restored.function_id == expected
        assert restored.to_data() == function.to_data()


def rejected(operation, label):
    try:
        operation()
    except ArtifactError as error:
        expected = {
            'summary identity': 'root/function identity disagrees',
            'callee identity': 'callee identity disagrees',
            'observation root': 'unknown root or edge',
            'run root': 'unknown root',
            'duplicate root': 'duplicate root id',
            'empty name': 'nonempty string',
            'non-string name': 'nonempty string',
            'duplicate owner': 'duplicates',
            'ABI': 'canonical identifier',
            'internal ID': 'canonical identifier',
        }
        assert expected[label] in str(error), str(error)
        return
    raise AssertionError('corruption escaped validator: ' + label)


def check_links(artifact):
    restored = ExtractionArtifact.parse(artifact.canonical_json())
    assert restored == artifact
    assert tuple(root.root_id for root in restored.roots) == tuple(sorted(NAMES))
    assert tuple(root.function_id for root in restored.roots) == tuple(sorted(NAMES))
    assert restored.observations[0].root_id == '_Py'
    assert restored.runs[0].root_id == '_Py'
    assert restored.summary_applications[0].root_id == '_Py'
    assert restored.summary_applications[0].callee_function_id == 'Py'
    assert restored.function_summaries[0].function_id == 'Py'
    assert restored.function_summaries[0].root_id == 'Py'


def check_corruption_controls(functions, artifact):
    # The negative controls independently corrupt each owner. They must fail
    # in check_names even when its assertion loop is mutated away.
    count = 0
    for index, function in enumerate(functions):
        changed = replace(function, occurrences=tuple(
            replace(item, origin=replace(item.origin, function_owners=('wrong',)))
            for item in function.occurrences))
        corrupted = (*functions[:index], changed, *functions[index + 1:])
        try:
            check_names(corrupted)
        except AssertionError:
            count += 1
        else:
            raise AssertionError('corruption escaped checker: owner')
    assert count == len(NAMES)
    # Reference validation must still distinguish the actual names, even when
    # both are legal and differ only by a leading underscore.
    rejected(lambda: replace(artifact, function_summaries=(replace(
        artifact.function_summaries[0], function_id='_Py'),)), 'summary identity')
    rejected(lambda: replace(artifact, summary_applications=(replace(
        artifact.summary_applications[0], callee_function_id='_Py'),)), 'callee identity')
    rejected(lambda: replace(artifact, observations=(replace(
        artifact.observations[0], root_id='missing@root'),)), 'observation root')
    rejected(lambda: replace(artifact, runs=(replace(
        artifact.runs[0], root_id='missing@root'),)), 'run root')
    rejected(lambda: replace(artifact, roots=(*artifact.roots, artifact.roots[0])), 'duplicate root')


EXTERNAL_FIELDS = (
    ('function_owners',), ('root_id', 'function_id'), ('root_id',),
    ('function_id', 'root_id'), ('root_id', 'callee_function_id'),
    ('root_id',), ('symbol',),
)


def assert_external_fields(data, fields, name):
    checked = 0
    for field in fields:
        assert data[field] == ([name] if field == 'function_owners' else name)
        checked += 1
    assert checked == len(fields)


def check_constructors():
    """Focused artifact checks can run without a native symbolic runtime."""
    step = StepSummary(TypedExpr.bool_lit(True), (), Target('address', 1),
                       TypedExpr.bv_lit(64, 1))
    edge = EdgeId(StaticOccurrenceId(0), OutcomeId(0))
    count = 0
    # NUL is representable in JSON/provider IDs, but terminates ELF strings.
    artifact_names = (*NAMES, 'prefix\0suffix')
    for name in artifact_names:
        objects = (
            DecodedInstructionEvidence('0' * 64, 1, 'c3', 'AMD64', '64', 'ret', (name,)),
            Root(name, name, 1, 'sysv', 'true'),
            ContextObservation('observation.1', name, edge, PrefixSummary.empty(), step, 'true'),
            FunctionSummary('summary.1', name, name, 'true', step, ()),
            SummaryApplication('application.1', name, edge, name, 'summary.1',
                               'identity', 'true', 'ordinary', Target('address', 1),
                               PrefixSummary.nonempty('call', 1), step),
            ContextRun('run.1', name, (RunEvent('observation', 'observation.1'),)),
            PrimitiveModelEvidence('0' * 64, 1, name, 'plt', 'sysv', 'model',
                                   '1' * 64, 'true', 'identity', 'return', ('proof',)),
        )
        for obj, fields in zip(objects, EXTERNAL_FIELDS, strict=True):
            data = json.loads(json.dumps(obj.to_data()))
            assert_external_fields(data, fields, name)
            assert type(obj).from_data(data) == obj
            for field in fields:
                corrupted = dict(data, **{field: ['wrong'] if field == 'function_owners' else 'wrong'})
                try:
                    assert_external_fields(corrupted, fields, name)
                except AssertionError:
                    pass
                else:
                    raise AssertionError('corruption escaped checker: external field')
            count += 1
    assert count == 7 * len(artifact_names)
    rejected(lambda: Root('', 'Py', 1, 'sysv', 'true'), 'empty name')
    rejected(lambda: DecodedInstructionEvidence('0' * 64, 1, 'c3', 'AMD64', '64', 'ret', ('_Py', '_Py')), 'duplicate owner')
    rejected(lambda: Root('Py', 123, 1, 'sysv', 'true'), 'non-string name')
    rejected(lambda: Root('Py', 'Py', 1, 'invalid abi', 'true'), 'ABI')
    rejected(lambda: ContextObservation('invalid id', 'Py', edge,
                                        PrefixSummary.empty(), step, 'true'), 'internal ID')
    from extractor.elf_fixture import write_fixture
    from extractor.elf_symbol_names import (
        SymbolEncodingError,
        validate_elf_symbol_encoding,
    )

    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / 'names.elf'
        write_fixture(path, tuple((name, index * 16, b'\xc3', False, False)
                                 for index, name in enumerate(NAMES)))
        validate_elf_symbol_encoding(path)
        write_fixture(path, ((b'\xff', 0, b'\xc3', False, False),
                             (b'\xfe', 16, b'\xc3', False, False),
                             ('valid', 32, b'\xc3', False, False)))
        validate_elf_symbol_encoding(path, {'valid'})
        try:
            validate_elf_symbol_encoding(path, {'�'})
        except SymbolEncodingError as error:
            assert 'replacement decoding would lose its identity' in str(error)
        else:
            raise AssertionError('lossy ELF names were silently accepted')
    check_sectionless_symbol_names()
    return count


def check_sectionless_symbol_names():
    """PT_DYNAMIC auditing must filter raw names before strict decoding."""
    from elftools.elf.dynamic import DynamicSegment
    from elftools.elf.elffile import ELFFile

    from extractor.elf_symbol_names import (
        SymbolEncodingError,
        validate_elf_symbol_encoding,
    )

    # ELF64 with no section headers: one load segment, PT_DYNAMIC, a SysV
    # hash table declaring four dynsym entries, and their raw string table.
    raw = bytearray(0x400)
    raw[:64] = struct.pack('<16sHHIQQQIHHHHHH', b'\x7fELF\x02\x01\x01' + bytes(9),
                          3, 62, 1, 0, 64, 0, 0, 64, 56, 2, 64, 0, 0)
    raw[64:120] = struct.pack('<IIQQQQQQ', 1, 4, 0, BASE, BASE, len(raw), len(raw), 0x1000)
    raw[120:176] = struct.pack('<IIQQQQQQ', 2, 4, 0x200, BASE + 0x200,
                              BASE + 0x200, 6 * 16, 6 * 16, 8)
    raw[0x200:0x260] = b''.join(struct.pack('<qQ', tag, value) for tag, value in (
        (4, BASE + 0x300), (5, BASE + 0x340), (6, BASE + 0x280),
        (10, 16), (11, 24), (0, 0),
    ))
    raw[0x300:0x31c] = struct.pack('<7I', 1, 4, 1, 0, 2, 3, 0)
    raw[0x340:0x350] = b'\0valid\0\xffbad\0\xef\xbf\xbd\0'
    for index, name_offset in enumerate((1, 7, 12), 1):
        start = 0x280 + index * 24
        raw[start:start + 24] = struct.pack('<IBBHQQ', name_offset, 0x12, 0, 1,
                                          BASE + 0x380 + index, 1)
    raw[0x381:0x384] = b'\xc3\xc3\xc3'
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / 'sectionless.elf'
        path.write_bytes(raw)
        with path.open('rb') as stream:
            elf = ELFFile(stream)
            assert elf.num_sections() == 0
            tables = [segment for segment in elf.iter_segments() if isinstance(segment, DynamicSegment)]
            assert len(tables) == 1
            assert tables[0].num_symbols() == 4
            assert tables[0].get_table_offset('DT_SYMTAB') == (BASE + 0x280, 0x280)
        validate_elf_symbol_encoding(path, {'valid'})
        validate_elf_symbol_encoding(path, {'�'})  # literal U+FFFD remains valid
        validate_elf_symbol_encoding(path, set())
        checked = []
        for names in (None, {'�bad'}):
            try:
                validate_elf_symbol_encoding(path, names)
            except SymbolEncodingError as error:
                assert 'bytes=ff626164' in str(error)
                assert 'at 0x347' in str(error)
                assert 'replacement decoding would lose its identity' in str(error)
                checked.append(names)
            else:
                raise AssertionError('lossy sectionless ELF name was silently accepted')
        assert checked == [None, {'�bad'}]


def check_inventory_collisions():
    """A generated library key must never replace a literal ELF spelling."""
    from extractor.native_runtime import preload_libstdcxx

    preload_libstdcxx()
    import angr

    from extractor.binary_cfg import build_static_cfg
    from extractor.binary_inventory import (
        PinnedBinary,
        exact_symbol_inventory_policy,
        inventory_project,
    )
    from extractor.elf_fixture import write_fixture
    from extractor.fresh import FreshFunction, extract_fresh_function

    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        main_path, library_path = directory / 'main.elf', directory / 'lib.so'
        literal_names = ('lib.so:foo bar', 'lib.so:foo bar@501000',
                         'lib.so:foo bar@501000@')
        literal_code = b'\xb8\x11\x00\x00\x00\xc3'
        library_code = b'\xb8\x22\x00\x00\x00\xc3'
        call_address, library_address = 0x401040, 0x501000
        write_fixture(main_path, (
            ('foo bar', 0, b'\xc3', False, False),
            (literal_names[0], 16, literal_code, False, False),
            (literal_names[1], 32, b'\xc3', False, False),
            (literal_names[2], 48, b'\xc3', False, False),
            ('caller', 64, b'\xe8' + struct.pack('<i', library_address - call_address - 5)
             + b'\xc3', False, False),
        ))
        write_fixture(library_path, (('foo bar', 0, library_code, False, False),), elf_type=3)
        project = angr.Project(str(main_path), auto_load_libs=False, load_options={
            'force_load_libs': [str(library_path)],
            'lib_opts': {str(library_path): {'base_addr': 0x500000}},
        })
        policy = exact_symbol_inventory_policy((*literal_names, 'caller'), open_transfers=True)
        manifest = inventory_project(project, main_path, policy)
        alias = 'lib.so:foo bar@501000@@'
        expected_addresses = {literal_names[0]: 0x401010, literal_names[1]: 0x401020,
                              literal_names[2]: 0x401030, 'caller': call_address,
                              alias: library_address}
        assert {name: root['address'] for name, root in manifest['roots'].items()} == expected_addresses
        assert {name: manifest['roots'][name]['symbol'] for name in literal_names} == dict(zip(literal_names, literal_names))
        assert manifest['call_graph']['caller'] == {alias: 1}
        assert manifest['roots'][alias]['symbol'] == 'foo bar'
        assert manifest['roots'][alias]['object_path'] == str(library_path)
        assert manifest['roots'][literal_names[0]]['object_path'] == str(main_path)
        # Exercise extraction and its serialized owners, not just lookup keys.
        pinned = PinnedBinary(main_path, manifest, project)
        cfg = build_static_cfg(pinned)
        observed = []
        for name, expected_code, expected_address in (
            (literal_names[0], literal_code, 0x401010), (alias, library_code, library_address),
        ):
            function = extract_fresh_function(pinned, cfg, name)
            restored = FreshFunction.from_data(json.loads(function.canonical_json()))
            assert restored.function_id == name
            assert restored.entry == expected_address
            assert [item.origin.function_owners for item in restored.occurrences] == [(name,), (name,)]
            assert ''.join(item.origin.instruction_bytes for item in restored.occurrences) == expected_code.hex()
            observed.append(restored.entry)
        assert observed == [0x401010, 0x501000]


def main():
    from extractor.native_runtime import preload_libstdcxx

    preload_libstdcxx()
    from extractor.binary_cfg import build_static_cfg
    from extractor.binary_inventory import (
        InventoryError,
        exact_symbol_inventory_policy,
        inventory,
        inventory_project,
        load_pinned_binary,
    )
    from extractor.elf_fixture import write_fixture
    from extractor.fresh import extract_fresh_function

    check_inventory_collisions()
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / 'names.elf'
        manifest_path = Path(temporary) / 'manifest.json'
        # _Py calls Py; all other symbols are one-byte RET functions.
        fixtures = tuple((name, index * 16,
                          b'\xe8\x0b\x00\x00\x00\xc3' if index == 0 else b'\xc3',
                          False, False) for index, name in enumerate(NAMES))
        write_fixture(path, fixtures)
        # Distinct invalid byte names collapse under the provider's replacement
        # decoder. Neither may silently become the valid literal U+FFFD above.
        invalid_path = Path(temporary) / 'invalid-names.elf'
        write_fixture(invalid_path, ((b'\xff', 0, b'\xc3', False, False),
                                     (b'\xfe', 16, b'\xc3', False, False)))
        try:
            inventory(invalid_path, exact_symbol_inventory_policy(('�',)))
        except InventoryError as error:
            assert 'replacement decoding would lose its identity' in str(error)
            assert 'bytes=ff' in str(error) or 'bytes=fe' in str(error)
        else:
            raise AssertionError('lossy ELF names were silently accepted')
        write_fixture(invalid_path, ((b'\xff', 0, b'\xc3', False, False),
                                     ('valid', 16, b'\xc3', False, False)), elf_type=3)
        unrelated = inventory(invalid_path, exact_symbol_inventory_policy(('valid',)))
        assert tuple(unrelated['roots']) == ('valid',)
        # Equal decoded spellings in an unrelated object are a separate name
        # domain: its invalid bytes must not poison this valid literal U+FFFD.
        import angr
        project = angr.Project(str(path), auto_load_libs=False,
                               load_options={'force_load_libs': [str(invalid_path)]})
        scoped = inventory_project(project, path, exact_symbol_inventory_policy(('�',)))
        assert scoped['roots']['�']['address'] == BASE + TEXT_OFFSET + 10 * 16
        policy = exact_symbol_inventory_policy(NAMES)
        manifest = inventory(path, policy)
        assert set(manifest['roots']) == set(NAMES)
        assert {name: value['symbol'] for name, value in manifest['roots'].items()} == dict(zip(NAMES, NAMES))
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        pinned = load_pinned_binary(path, manifest_path, policy)
        cfg = build_static_cfg(pinned)
        functions = tuple(extract_fresh_function(pinned, cfg, name) for name in NAMES)
        check_names(functions)
        call = next(edge for edge in functions[0].local_edges if edge.source == BASE + TEXT_OFFSET)
        continuation = Target('address', BASE + TEXT_OFFSET + 5)
        after = replace(call.summary, target=continuation)
        summary = FunctionSummary('summary.1', 'Py', 'Py', 'true', functions[1].local_edges[0].summary, ())
        application = SummaryApplication('application.1', '_Py', call.id, 'Py', 'summary.1',
                                         'identity', 'true', 'ordinary', continuation,
                                         PrefixSummary.nonempty('call', BASE + TEXT_OFFSET + 16), after)
        observation = ContextObservation('observation.1', '_Py', call.id, PrefixSummary.empty(), call.summary, 'true')
        artifact = ExtractionArtifact(
            manifest['image_sha256'], functions[0].declarations,
            tuple(item for function in functions for item in function.occurrences),
            tuple(sorted((Root(name, name, BASE + TEXT_OFFSET + index * 16, 'sysv', 'true')
                          for index, name in enumerate(NAMES)), key=lambda root: root.root_id)),
            tuple(item for function in functions for item in function.local_edges),
            (observation,), (application,),
            (ContextRun('run.1', '_Py', (RunEvent('observation', 'observation.1'),
                                       RunEvent('summary_application', 'application.1'))),), (summary,))
        check_links(artifact)
        check_corruption_controls(functions, artifact)
        count = check_constructors()
    print(json.dumps({'symbols': NAMES, 'constructor_roundtrips': count,
                      'pipeline': 'real ELF / inventory / CFG / extraction / JSON / linked artifact'}))


if __name__ == '__main__':
    import sys
    if sys.argv[1:] == ['--artifact-only']:
        print(json.dumps({'constructor_roundtrips': check_constructors()}))
    else:
        main()
