#!/usr/bin/env bash
set -euo pipefail
export PATH=/nix/store/qpk7v7b4ixkpa4jfsvgmmsmdr4l23in1-lean/bin:/run/current-system/sw/bin
export LEAN_NUM_THREADS=1
export BWRAP=/nix/store/mvj6y8k3xs35cj7kq937xi44q4hl3r93-bubblewrap-0.12.0/bin/bwrap
root=/home/heartpunk/workspaces/observer-shim-proof-65844e28
bash "$root/experiments/mov_observer/native_observer/build.sh"
bash "$root/experiments/mov_observer/native_observer/run.sh"
