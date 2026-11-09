#!/usr/bin/env bash
set -euo pipefail
export PATH=/nix/store/qpk7v7b4ixkpa4jfsvgmmsmdr4l23in1-lean/bin:/run/current-system/sw/bin
export LEAN_NUM_THREADS=1
snapshot=/home/heartpunk/workspaces/observer-fix5-33d9bcd7
task_root=$snapshot/experiments/mov_observer
printf 'snapshot='; git -C "$snapshot" rev-parse HEAD
sha256sum "$task_root/WholeObserver.lean"
lean --version
cd /tmp/wruh-mov-observer-20261106/ayxg
printf 'ayxg='; git rev-parse HEAD
lake env bash -c '
set -euo pipefail
task_root=$1
export LEAN_PATH="$task_root:/home/heartpunk/workspaces/observer-cleanup-e7f7a9d2/experiments/mov_observer:$task_root/models:/tmp/wruh-mov-observer-20261106/out:$LEAN_PATH"
cd "$task_root"
for module in NativeBoundary Bridge Transfer VectorProtocol LegacyFp FaultProtocol WholeObserver; do
  echo "$module"
  lean -o "$module.olean" "$module.lean"
done
' bash "$task_root"
