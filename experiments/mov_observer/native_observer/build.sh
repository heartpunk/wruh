#!/usr/bin/env bash
set -euo pipefail
# Invoke on Linux in the pinned Lean 4.34 environment.
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export LEAN_NUM_THREADS=${LEAN_NUM_THREADS:-1}
mkdir -p "$root/out"
cp "$root/../native_shim/MemoryWrite.lean" "$root/Observer.lean" "$root/Trials.lean" "$root/FpTrials.lean" "$root/out/"
cd "$root/out"
export LEAN_PATH=".$(test -z "${LEAN_PATH:-}" || printf ':%s' "$LEAN_PATH")"
lean --version
sha256sum "$root/Observer.lean" "$root/Trials.lean" "$root/FpTrials.lean" "$root/transport.S" "$root/../native_shim/write_memory.S" "$root/../fixtures/loader.bin" "$root/../fixtures/observer.bin"
lean -o MemoryWrite.olean -c MemoryWrite.c MemoryWrite.lean
lean -o Observer.olean -c Observer.c Observer.lean
lean -o Trials.olean -c Trials.c Trials.lean
leanc -O2 MemoryWrite.c Observer.c Trials.c "$root/transport.S" "$root/../native_shim/write_memory.S" -o trials
lean -o FpTrials.olean -c FpTrials.c FpTrials.lean
leanc -O2 MemoryWrite.c Observer.c FpTrials.c "$root/transport.S" "$root/../native_shim/write_memory.S" -o fp-trials
