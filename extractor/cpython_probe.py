"""Static extraction of selected functions from the exact extraction CPython."""
from extractor.runtime_trace import start_runtime_trace

start_runtime_trace()
from extractor.native_runtime import preload_libstdcxx

preload_libstdcxx()
import argparse
import hashlib
import json
import tempfile
from dataclasses import replace
from pathlib import Path

from ayxg.codec import dumps

from extractor.binary_cfg import build_static_cfg
from extractor.binary_inventory import (
    PinnedBinary,
    exact_symbol_inventory_policy,
    inventory_project,
)
from extractor.fresh import extract_fresh_function
from extractor.loaded_image import load_object_set, loaded_image_data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--identity', type=Path, required=True)
    parser.add_argument('--object', type=Path, action='append', required=True)
    parser.add_argument('--root', required=True)
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
        project = load_object_set(actual[main_hash], specification)
        policy = replace(exact_symbol_inventory_policy((args.root,), open_transfers=True),
                         discover_direct_targets=False)
        manifest = inventory_project(project, actual[main_hash], policy)
        pinned = PinnedBinary(actual[main_hash], manifest, project)
        cfg = build_static_cfg(pinned)
        function = extract_fresh_function(pinned, cfg, args.root)
        result = {'schema': 'wruh-cpython-extraction-v1', 'identity': identity,
                  'selection': 'one exact function; other transfers remain open',
                  'root': args.root, 'manifest': manifest, 'cfg': cfg,
                  'function': function.to_data(), 'loaded_image': loaded_image_data(project),
                  'native_candidate_execution': False}
        args.output.write_text(dumps(result, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
