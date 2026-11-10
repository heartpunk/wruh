#!/usr/bin/env bash
set -euo pipefail
export PATH=/nix/store/qpk7v7b4ixkpa4jfsvgmmsmdr4l23in1-lean/bin:/run/current-system/sw/bin
export LEAN_NUM_THREADS=1
task_root=/home/heartpunk/workspaces/observer-shim-proof-65844e28/experiments/mov_observer/native_shim/proof
cd /tmp/wruh-mov-observer-20261106/ayxg
lake env bash -c '
set -euo pipefail
export LEAN_PATH="$1:/home/heartpunk/workspaces/observer-install-66180fb2/experiments/mov_observer:/home/heartpunk/workspaces/observer-cleanup-e7f7a9d2/experiments/mov_observer:/tmp/wruh-mov-observer-20261106/out:$LEAN_PATH"
cd "$1"
sha256sum ShimModel.lean ShimProof.lean
lean -o ShimProof.olean ShimProof.lean
' bash "$task_root"
