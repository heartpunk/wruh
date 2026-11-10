#!/usr/bin/env bash
set -euo pipefail
# Run inside a bounded fleet-build.slice child; preserve the existing out cache.
cd /home/heartpunk/workspaces/observer-shim-proof-65844e28
nix develop .#nativeObserver --command bash -c '
  set -euo pipefail
  bash experiments/mov_observer/native_observer/build.sh
  OBSERVER_TRIALS=trials bash experiments/mov_observer/native_observer/run.sh
'
