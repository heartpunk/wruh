#!/usr/bin/env bash
set -euo pipefail
task_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "$task_root/../.." && pwd)
export AYXG_WORKSPACE=${AYXG_WORKSPACE:-"$repo_root/../ayxg-mov-observer"}
: "${AYXG_FLOATLIB_SOURCE:?Run through the pinned Nix development environment}"
export LEAN_NUM_THREADS=${LEAN_NUM_THREADS:-4}
cd "$task_root"
mkdir -p out
python3 - <<'PY'
import os
from pathlib import Path
import re
roots = {'Ayxg': Path(os.environ['AYXG_WORKSPACE']),
         'FloatLib': Path(os.environ['AYXG_FLOATLIB_SOURCE'])}
pending = ['Ayxg.QfAbv.Step', 'Ayxg.LTS.QfAbv.SymbolicTransitionSystem']
seen, mathlib = set(), set()
while pending:
    module = pending.pop()
    if module in seen:
        continue
    seen.add(module)
    prefix = module.split('.')[0]
    if prefix == 'Mathlib':
        mathlib.add(module)
    elif prefix in roots:
        source = roots[prefix] / (module.replace('.', '/') + '.lean')
        pending.extend(re.findall(r'^\s*(?:(?:public|meta)\s+)*import\s+([\w.]+)',
                                  source.read_text(), re.M))
assert mathlib, 'No Mathlib imports found; do not download the entire cache'
Path('out/mathlib-cache-roots.txt').write_text('\n'.join(sorted(mathlib)) + '\n')
PY
mapfile -t cache_roots < out/mathlib-cache-roots.txt
cd "$AYXG_WORKSPACE"
# Resolving the exact pinned packages precedes requesting their cache.
lake resolve-deps
lake exe cache get "${cache_roots[@]}"
bash "$task_root/check_pipeline.sh"

