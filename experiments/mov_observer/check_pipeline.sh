#!/usr/bin/env bash
set -euo pipefail
task_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "$task_root/../.." && pwd)
ayxg_root=${AYXG_WORKSPACE:-"$repo_root/../ayxg-mov-observer"}
test -f "$ayxg_root/Ayxg/QfAbv/Step.lean"
: "${AYXG_FLOATLIB_SOURCE:?Run through the pinned Nix development environment}"
export LEAN_NUM_THREADS=${LEAN_NUM_THREADS:-4}
mkdir -p "$task_root/out"
cp "$task_root"/{Proof,ByteCodec,Pipeline,Protocol}.lean "$task_root/out/"
cp "$task_root/models/"*.lean "$task_root/out/"
cd "$ayxg_root"
lake build Ayxg.QfAbv.Step Ayxg.LTS.QfAbv.SymbolicTransitionSystem
lake env bash -c '
  set -euo pipefail
  task_root=$1
  export LEAN_PATH="$task_root/out${LEAN_PATH:+:$LEAN_PATH}"
  cd "$task_root/out"
  for module in Extracted Proof ByteCodec InputModel Pipeline Protocol; do
    lean -o "$module.olean" "$module.lean"
  done
' bash "$task_root"

