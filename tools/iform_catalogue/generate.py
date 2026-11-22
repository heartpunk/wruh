#!/usr/bin/env python3
"""Enumerate decoded occurrences in a complete binary-census function archive."""
import argparse
import json
import hashlib
import subprocess
import tarfile
from collections import defaultdict
from pathlib import Path

import iced_x86 as iced


def validate_census(archive, summary_path, entries_path):
    summary = json.loads(summary_path.read_text())
    if summary['interrupted'] or summary['attempted'] != summary['inventoryCandidates']:
        raise ValueError('census is incomplete or sampled')
    if summary['sampling']['samplingPolicy'] != 'full-census-v1':
        raise ValueError('census is not a full census')
    if hashlib.sha256(archive.read_bytes()).hexdigest() != summary['artifactArchiveSha256']:
        raise ValueError('archive digest does not match summary')
    entries = [json.loads(line) for line in entries_path.read_text().splitlines()]
    if len(entries) != summary['inventoryCandidates']:
        raise ValueError('ledger does not cover inventory')
    expected = [e['artifact'] for e in entries if e['disposition'] == 'extracted']
    if len(expected) != summary['dispositions'].get('extracted', 0) or len(set(expected)) != len(expected):
        raise ValueError('extracted ledger entries are inconsistent')
    with tarfile.open(archive, 'r:gz') as tar:
        actual = [m.name for m in tar.getmembers()]
    if sorted(actual) != sorted(expected):
        raise ValueError('archive does not match extracted ledger entries')
    return summary


def generate_many(censuses, xed):
    """Aggregate distinct bytes across (archive, target ID, binary SHA-256)."""
    occurrences = defaultdict(list)
    for archive, target_id, binary_sha256 in censuses:
        with tarfile.open(archive, 'r:gz') as tar:
            for member in sorted(tar.getmembers(), key=lambda m: m.name):
                if not member.isfile() or not member.name.startswith('functions/') or not member.name.endswith('.json'):
                    raise ValueError(f'unexpected archive member: {member.name}')
                with tar.extractfile(member) as stream:
                    function = json.load(stream)
                for occurrence in function['occurrences']:
                    origin = occurrence['origin']
                    if origin['kind'] != 'decoded_instruction':
                        raise ValueError(f'unexpected origin: {origin["kind"]}')
                    if origin['architecture'] != 'AMD64' or origin['decode_mode'] != 'long64':
                        raise ValueError('only AMD64 long64 is supported')
                    if binary_sha256 is not None and origin['image_sha256'] != binary_sha256:
                        raise ValueError('occurrence belongs to a different image')
                    raw = bytes.fromhex(origin['instruction_bytes'])
                    decoder = iced.Decoder(64, raw, ip=origin['canonical_address'])
                    instruction = decoder.decode()
                    if instruction.is_invalid or instruction.len != len(raw) or decoder.can_decode:
                        raise ValueError(f'iced cannot decode entire instruction: {raw.hex()}')
                    ref = {'@type': 'SourceOccurrence', 'function_id': function['function_id'],
                           'address': origin['canonical_address'],
                           'occurrence_id': occurrence['static_occurrence_id']}
                    if target_id is not None:
                        ref.update(target_id=target_id, binary_sha256=binary_sha256)
                    occurrences[(raw.hex(), instruction.code)].append(ref)
    keys = sorted(occurrences)
    result = subprocess.run([str(xed)], input=''.join(k[0] + '\n' for k in keys),
                            text=True, capture_output=True, check=True)
    classifications = result.stdout.splitlines()
    if len(classifications) != len(keys):
        raise ValueError('XED returned a different number of classifications')
    for (hex_bytes, code), classification in zip(keys, classifications):
        iform, width = classification.split('\t')
        yield {'@context': 'context.jsonld', '@type': 'EncodingRecord', 'iform': iform, 'iced_code': code,
               'bytes': hex_bytes, 'bitness': 64, 'operand_width': int(width),
               'occurrences': sorted(occurrences[(hex_bytes, code)],
                   key=lambda o: (o.get('target_id', ''), o.get('binary_sha256', ''),
                                  o['function_id'], o['address'], o['occurrence_id']))}


def generate(archive, xed, binary_sha256=None):
    return generate_many([(archive, None, binary_sha256)], xed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--census', type=Path, action='append', required=True,
                        help='complete census directory; repeat for each target')
    parser.add_argument('--xed', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    censuses = []
    seen = set()
    for directory in args.census:
        archive = directory / 'function-artifacts.tar.gz'
        summary = validate_census(archive, directory / 'summary.json', directory / 'entries.jsonl')
        identity = (summary['targetId'], summary['binarySha256'])
        if identity in seen:
            raise ValueError(f'duplicate census identity: {identity}')
        seen.add(identity)
        censuses.append((archive, *identity))
    rows = list(generate_many(censuses, args.xed))
    args.output.write_text(''.join(json.dumps(row, sort_keys=True, separators=(',', ':')) + '\n' for row in rows))


if __name__ == '__main__':
    main()
