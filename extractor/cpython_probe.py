"""Static instruction extraction from the exact extraction CPython."""
from extractor.runtime_trace import start_runtime_trace
start_runtime_trace()
from extractor.native_runtime import preload_libstdcxx
preload_libstdcxx()
import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from ayxg.codec import dumps
from extractor.loaded_image import loaded_image_data
from extractor.linear_pipeline import prepare
from extractor.fresh import extract_linear
from types import SimpleNamespace


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--identity', type=Path, required=True)
    parser.add_argument('--object', type=Path, action='append', required=True)
    parser.add_argument('--data-intervals', type=Path)
    parser.add_argument('--chunk-size', type=int, default=256)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    identity = json.loads(args.identity.read_text())
    expected = {record['sha256']: record for record in identity['objects']}
    actual = {hashlib.sha256(path.read_bytes()).hexdigest(): path.resolve() for path in args.object}
    if set(actual) != set(expected):
        raise ValueError('declared CPython object identities differ from recorded extraction runtime')
    main_hash = next(sha for sha, record in expected.items() if record['resolved_path'].endswith('/libpython3.12.so.1.0'))
    libraries = [sha for sha, record in expected.items()
                 if sha != main_hash and not record['resolved_path'].endswith('/bin/python3.12')]
    with tempfile.TemporaryDirectory() as directory:
        specification = Path(directory) / 'objects.json'
        specification.write_text(json.dumps([{'path': str(actual[sha]), 'sha256': sha,
            'base_addr': 0x10000000 * (index + 1)} for index, sha in enumerate(sorted(libraries))]))
        selection = SimpleNamespace(artifact=actual[main_hash], objects=specification,
                                    data_intervals=args.data_intervals,
                                    chunk_size=args.chunk_size, seed=args.seed)
        project, records, report, image_sha256 = prepare(selection)
        result = {'schema': 'wruh-cpython-extraction-v2', 'identity': identity,
                  'image_sha256': image_sha256, 'inventory': report,
                  'extraction': extract_linear(project, records).to_data(),
                  'loaded_image': loaded_image_data(project),
                  'native_candidate_execution': False}
        args.output.write_text(dumps(result, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
