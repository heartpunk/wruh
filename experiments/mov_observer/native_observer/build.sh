#!/usr/bin/env bash
set -euo pipefail
# Invoke on Linux in the pinned Lean 4.34 environment.
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export LEAN_NUM_THREADS=${LEAN_NUM_THREADS:-1}
mkdir -p "$root/out"
cp "$root/../native_shim/MemoryWrite.lean" "$root/InstallationEncoding.lean" "$root/FlagsBuffer.lean" "$root/Observer.lean" "$root/Trials.lean" "$root/FpTrials.lean" "$root/VectorTrials.lean" "$root/FaultTrials.lean" "$root/out/"
cd "$root/out"
export LEAN_PATH=".$(test -z "${LEAN_PATH:-}" || printf ':%s' "$LEAN_PATH")"
lean --version
sha256sum "$root/vector-cases.S" "$root/InstallationEncoding.lean" "$root/FlagsBuffer.lean" "$root/Observer.lean" "$root/Trials.lean" "$root/FpTrials.lean" "$root/VectorTrials.lean" "$root/FaultTrials.lean" "$root/transport.S" "$root/../native_shim/write_memory.S" "$root/../fixtures/loader.bin" "$root/../fixtures/observer.bin"
lean -o MemoryWrite.olean -c MemoryWrite.c MemoryWrite.lean
lean -o InstallationEncoding.olean -c InstallationEncoding.c InstallationEncoding.lean
lean -o FlagsBuffer.olean -c FlagsBuffer.c FlagsBuffer.lean
lean -o Observer.olean -c Observer.c Observer.lean
lean -o Trials.olean -c Trials.c Trials.lean
leanc -O2 MemoryWrite.c InstallationEncoding.c FlagsBuffer.c Observer.c Trials.c "$root/transport.S" "$root/../native_shim/write_memory.S" -o trials
lean -o FpTrials.olean -c FpTrials.c FpTrials.lean
leanc -O2 MemoryWrite.c InstallationEncoding.c FlagsBuffer.c Observer.c FpTrials.c "$root/transport.S" "$root/../native_shim/write_memory.S" -o fp-trials
lean -o VectorTrials.olean -c VectorTrials.c VectorTrials.lean
leanc -O2 MemoryWrite.c InstallationEncoding.c FlagsBuffer.c Observer.c VectorTrials.c "$root/transport.S" "$root/../native_shim/write_memory.S" -o vector-trials
as --64 "$root/vector-cases.S" -o vector-cases.o
for name in paddq-xmm vpxor-ymm vpaddq-zmm vpaddq-merge-high vpaddq-zero-high vmovdqu64-store kxorq; do
  objcopy -O binary --only-section=".text.$name" vector-cases.o "$name.bin"
done
objdump -d -Mintel vector-cases.o
lean -o FaultTrials.olean -c FaultTrials.c FaultTrials.lean
leanc -O2 MemoryWrite.c InstallationEncoding.c FlagsBuffer.c Observer.c FaultTrials.c "$root/transport.S" "$root/../native_shim/write_memory.S" -o fault-trials
