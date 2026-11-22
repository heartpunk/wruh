import io
import json
import tarfile
from pathlib import Path

import pytest

import iced_x86 as iced
from tools.iform_catalogue.generate import generate


def archive(path, functions):
    with tarfile.open(path, 'w:gz') as tar:
        for function in functions:
            data = json.dumps(function).encode()
            info = tarfile.TarInfo(f'functions/{function["function_id"]}.json')
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))


def occurrence(address, ident, code):
    return {'static_occurrence_id': ident, 'origin': {
        'kind': 'decoded_instruction', 'architecture': 'AMD64', 'decode_mode': 'long64',
        'canonical_address': address, 'instruction_bytes': code}}


def test_aggregation_and_instruction_boundaries(tmp_path):
    source = tmp_path / 'functions.tar.gz'
    archive(source, [
        {'function_id': 'a', 'occurrences': [occurrence(4096, 1, '4889d8'), occurrence(4099, 2, 'c3')]},
        {'function_id': 'b', 'occurrences': [occurrence(8192, 3, '4889d8')]},
    ])
    xed = tmp_path / 'xed'
    xed.write_text('#!/usr/bin/env python3\nimport sys\nfor line in sys.stdin: print("FORM\\t64")\n')
    xed.chmod(0o755)
    rows = list(generate(source, xed))
    assert [r['bytes'] for r in rows] == ['4889d8', 'c3']
    assert rows[0]['iform'] == 'FORM' and rows[0]['bitness'] == 64
    assert rows[0]['occurrences'] == [
        {'@type': 'SourceOccurrence', 'function_id': 'a', 'address': 4096, 'occurrence_id': 1},
        {'@type': 'SourceOccurrence', 'function_id': 'b', 'address': 8192, 'occurrence_id': 3},
    ]
    archive(source, [{'function_id': 'a', 'occurrences': [occurrence(4096, 1, 'c3c3')]}])
    with pytest.raises(ValueError, match='entire instruction'):
        list(generate(source, xed))


def test_census_integrity_rejects_missing_extracted_member(tmp_path):
    import hashlib
    from tools.iform_catalogue.generate import validate_census

    source = tmp_path / 'functions.tar.gz'
    archive(source, [{'function_id': 'a', 'occurrences': []}])
    summary = tmp_path / 'summary.json'
    summary.write_text(json.dumps({
        'interrupted': False, 'attempted': 1, 'inventoryCandidates': 1,
        'sampling': {'samplingPolicy': 'full-census-v1'},
        'artifactArchiveSha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'dispositions': {'extracted': 1},
    }))
    entries = tmp_path / 'entries.jsonl'
    entries.write_text(json.dumps({'disposition': 'extracted', 'artifact': 'functions/b.json'}) + '\n')
    with pytest.raises(ValueError, match='archive does not match'):
        validate_census(source, summary, entries)


def test_occurrences_identify_their_source_census(tmp_path):
    from tools.iform_catalogue.generate import generate_many

    xed = tmp_path / 'xed'
    xed.write_text('#!/usr/bin/env python3\nimport sys\nfor line in sys.stdin: print("FORM\\t64")\n')
    xed.chmod(0o755)
    archives = []
    for target, digest in [('lua', 'a' * 64), ('quickjs', 'b' * 64)]:
        source = tmp_path / f'{target}.tar.gz'
        item = occurrence(4096, 1, 'c3')
        item['origin']['image_sha256'] = digest
        archive(source, [{'function_id': 'same', 'occurrences': [item]}])
        archives.append((source, target, digest))
    rows = list(generate_many(archives, xed))
    assert len(rows) == 1
    assert [(o['target_id'], o['binary_sha256']) for o in rows[0]['occurrences']] == [
        ('lua', 'a' * 64), ('quickjs', 'b' * 64)]


def test_jsonld_context_expansion_preserves_all_occurrence_evidence():
    from pyld import jsonld
    from rdflib import Graph, URIRef
    from rdflib.namespace import RDF, RDFS

    base = 'https://github.com/heartpunk/wruh/blob/main/data/iform-catalogue/vocabulary.ttl#'
    xsd = 'http://www.w3.org/2001/XMLSchema#'
    data_dir = Path(__file__).resolve().parents[1] / 'data' / 'iform-catalogue'
    context = json.loads((data_dir / 'context.jsonld').read_text())
    terms = context['@context']
    assert '@vocab' not in terms
    row_fields = {'iform', 'iced_code', 'bytes', 'bitness', 'operand_width', 'occurrences'}
    occurrence_fields = {'target_id', 'binary_sha256', 'function_id', 'address', 'occurrence_id'}
    class_terms = {'EncodingRecord', 'SourceOccurrence'}
    assert set(terms) == row_fields | occurrence_fields | class_terms
    graph = Graph().parse(data_dir / 'vocabulary.ttl', format='turtle')
    for name, value in terms.items():
        iri = value if isinstance(value, str) else value['@id']
        kind = RDFS.Class if name in class_terms else RDF.Property
        assert (URIRef(iri), RDF.type, kind) in graph

    record = {
        '@context': 'context.jsonld', '@type': 'EncodingRecord', 'iform': 'ADD_GPRv_GPRv_01', 'iced_code': 7,
        'bytes': '01c0', 'bitness': 64, 'operand_width': 32,
        'occurrences': [
            {'@type': 'SourceOccurrence', 'target_id': 'apache', 'binary_sha256': 'ab' * 32, 'function_id': 'fn_a',
             'address': 4562745, 'occurrence_id': 169},
            {'@type': 'SourceOccurrence', 'target_id': 'bun', 'binary_sha256': 'cd' * 32, 'function_id': 'fn_b',
             'address': 41469013, 'occurrence_id': 111},
        ],
    }
    requested = []
    def loader(url, options=None):
        requested.append(url)
        assert url == 'https://example.invalid/context.jsonld'
        return {'contextUrl': None, 'documentUrl': url, 'document': context}

    options = {'base': 'https://example.invalid/catalogue.jsonl', 'documentLoader': loader}
    expanded = jsonld.expand(record, options=options)
    integer = xsd + 'nonNegativeInteger'
    binary = xsd + 'hexBinary'
    value = lambda v, datatype=None: [{'@value': v, **({'@type': datatype} if datatype else {})}]
    expected = [{
        '@type': [base + 'EncodingRecord'],
        base + 'xedIform': value('ADD_GPRv_GPRv_01', xsd + 'string'),
        base + 'icedCode': value(7, integer), base + 'instructionBytes': value('01c0', binary),
        base + 'decodeBitness': value(64, integer), base + 'xedOperandWidth': value(32, integer),
        base + 'occurrence': [
            {'@type': [base + 'SourceOccurrence'], base + 'targetId': value('apache', xsd + 'string'), base + 'binarySha256': value('ab' * 32, binary),
             base + 'functionId': value('fn_a', xsd + 'string'), base + 'canonicalAddress': value(4562745, integer),
             base + 'staticOccurrenceId': value(169, integer)},
            {'@type': [base + 'SourceOccurrence'], base + 'targetId': value('bun', xsd + 'string'), base + 'binarySha256': value('cd' * 32, binary),
             base + 'functionId': value('fn_b', xsd + 'string'), base + 'canonicalAddress': value(41469013, integer),
             base + 'staticOccurrenceId': value(111, integer)},
        ],
    }]
    assert requested == ['https://example.invalid/context.jsonld']
    assert expanded == expected
    compacted = jsonld.compact(expanded, context)
    assert jsonld.expand(compacted) == expected

    # Every real row and nested occurrence is covered; unknown keys would be
    # silently discarded by expansion without this check.
    with (data_dir / 'catalogue.jsonl').open() as stream:
        for line in stream:
            row = json.loads(line)
            assert row['@context'] == 'context.jsonld'
            assert set(row) == row_fields | {'@context', '@type'}
            assert row['@type'] == 'EncodingRecord'
            assert all(set(o) == occurrence_fields | {'@type'} and o['@type'] == 'SourceOccurrence'
                       for o in row['occurrences'])


def test_source_descriptors_preserve_bytes_and_expand():
    import hashlib
    from pyld import jsonld
    from rdflib import Graph, URIRef
    from rdflib.namespace import RDF, RDFS

    root = Path(__file__).resolve().parents[1] / 'data' / 'iform-catalogue'
    context = json.loads((root / 'sources-context.jsonld').read_text())
    terms = context['@context']
    assert '@vocab' not in terms
    classes = {'SourceFileSet', 'SourceFile', 'CatalogueFile'}
    expected_terms = classes | {'files', 'source_run', 'extraction_revision', 'target_id',
        'binary_sha256', 'sha256', 'size_bytes', 'media_type', 'purpose', 'xed_version', 'iced_version', 'source_sets'}
    assert set(terms) == expected_terms
    graph = Graph().parse(root / 'vocabulary.ttl', format='turtle')
    for name, value in terms.items():
        iri = value if isinstance(value, str) else value['@id']
        assert (URIRef(iri), RDF.type, RDFS.Class if name in classes else RDF.Property) in graph

    base = 'https://github.com/heartpunk/wruh/blob/main/data/iform-catalogue/vocabulary.ttl#'
    xsd = 'http://www.w3.org/2001/XMLSchema#'
    by_kind = {
        'census.jsonld': 'application/ld+json', 'entries.jsonl': 'application/x-ndjson',
        'function-artifacts.tar.gz': 'application/gzip', 'progress.json': 'application/json',
        'summary.json': 'application/json',
    }
    for target in ('quickjs', 'lua', 'bun', 'apache'):
        directory = root / target
        manifest = json.loads((directory / 'sources.jsonld').read_text())
        assert manifest['@context'] == '../sources-context.jsonld'
        assert manifest['@type'] == 'SourceFileSet' and manifest['target_id'] == target
        assert {f['@id'] for f in manifest['files']} == set(by_kind)
        for f in manifest['files']:
            path = directory / f['@id']
            assert f['@type'] == 'SourceFile' and f['media_type'] == by_kind[f['@id']]
            assert f['purpose'] and f['size_bytes'] == path.stat().st_size
            assert f['sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
        def loader(url, options=None):
            assert url == 'https://example.invalid/sources-context.jsonld'
            return {'contextUrl': None, 'documentUrl': url, 'document': context}
        expanded = jsonld.expand(manifest, options={'base': f'https://example.invalid/{target}/sources.jsonld', 'documentLoader': loader})
        node = expanded[0]
        assert set(node) == {'@id', '@type', base+'targetId', base+'binarySha256', base+'sourceRun', base+'extractionRevision', base+'sourceFile'}
        assert node['@type'] == [base + 'SourceFileSet']
        assert node[base+'binarySha256'] == [{'@type': xsd+'hexBinary', '@value': manifest['binary_sha256']}]
        assert node[base+'sourceRun'] == [{'@id': manifest['source_run']}]
        assert node[base+'extractionRevision'] == [{'@id': manifest['extraction_revision']}]
        assert node['@id'] == f'https://example.invalid/{target}/sources.jsonld'
        assert node[base + 'targetId'] == [{'@type': xsd + 'string', '@value': target}]
        assert len(node[base + 'sourceFile']) == 5
        for item in node[base + 'sourceFile']:
            assert item['@type'] == [base + 'SourceFile']
            assert set(item) == {'@id', '@type', base + 'fileSha256', base + 'fileSizeBytes', base + 'mediaType', base + 'filePurpose'}
            name = item['@id'].rsplit('/', 1)[-1]
            source = next(f for f in manifest['files'] if f['@id'] == name)
            assert item['@id'] == f'https://example.invalid/{target}/{name}'
            for predicate, field, datatype in (
                ('fileSha256', 'sha256', 'hexBinary'), ('fileSizeBytes', 'size_bytes', 'nonNegativeInteger'),
                ('mediaType', 'media_type', 'string'), ('filePurpose', 'purpose', 'string'),
            ):
                assert item[base + predicate] == [{'@type': xsd + datatype, '@value': source[field]}]
        assert jsonld.expand(jsonld.compact(expanded, context)) == expanded

    info = json.loads((root / 'catalogue-info.jsonld').read_text())
    assert info['@type'] == 'CatalogueFile' and info['xed_version'] == '2026.07.15' and info['iced_version'] == '1.21.0'
    assert info['sha256'] == hashlib.sha256((root / 'catalogue.jsonl').read_bytes()).hexdigest()
    info['@context'] = context['@context']
    expanded = jsonld.expand(info, options={'base': 'https://example.invalid/'})
    assert expanded[0]['@type'] == [base + 'CatalogueFile']
    assert expanded[0][base+'xedVersion'] == [{'@type': xsd+'string', '@value': '2026.07.15'}]
    assert expanded[0][base+'icedVersion'] == [{'@type': xsd+'string', '@value': '1.21.0'}]
    assert set(expanded[0]) == {'@id', '@type', base+'fileSha256', base+'fileSizeBytes', base+'mediaType', base+'filePurpose', base+'xedVersion', base+'icedVersion', base+'sourceFileSet'}
    assert {item['@id'] for item in expanded[0][base+'sourceFileSet']} == {
        f'https://example.invalid/{target}/sources.jsonld' for target in ('quickjs', 'lua', 'bun', 'apache')}
