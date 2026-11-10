#!/usr/bin/env bash
set -euo pipefail
export PATH=/nix/store/qpk7v7b4ixkpa4jfsvgmmsmdr4l23in1-lean/bin:/run/current-system/sw/bin
export LEAN_NUM_THREADS=1
root=/home/heartpunk/workspaces/observer-shim-proof-65844e28/experiments/mov_observer
cd /tmp/wruh-mov-observer-20261106/ayxg
lake env bash -c '
set -euo pipefail
root=$1
export LEAN_PATH="$root/out/fidelity:$root/native_observer/out:/home/heartpunk/workspaces/observer-install-66180fb2/experiments/mov_observer:/home/heartpunk/workspaces/observer-cleanup-e7f7a9d2/experiments/mov_observer:/tmp/wruh-mov-observer-20261106/out:$LEAN_PATH"
cd "$root/out/fidelity"
lean --version
sha256sum Bootstrap.lean MovInstaller.lean MovCapturer.lean
for module in Bootstrap MovInstaller MovCapturer; do
  lean -o "$module.olean" "$module.lean"
done
' bash "$root"
