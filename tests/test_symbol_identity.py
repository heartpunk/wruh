"""Exact external identities through real ELF extraction and artifact links."""
import json
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
    return count


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
