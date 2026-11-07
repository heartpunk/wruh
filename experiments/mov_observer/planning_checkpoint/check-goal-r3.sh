#!/usr/bin/env bash
set -euo pipefail
export PATH=/run/current-system/sw/bin:/run/wrappers/bin:/home/heartpunk/.nix-profile/bin
task_root=$1
cd "$task_root"
date -u '+started_utc=%Y-%m-%dT%H:%M:%SZ'
git rev-parse HEAD
sha256sum experiments/mov_observer/ObserverEndToEndGoal.lean
export LEAN_NUM_THREADS=1
nix develop --option max-jobs 1 --option cores 1 --command bash -c '
  set -euo pipefail
  command -v lean
  lean --version
  lean experiments/mov_observer/ObserverEndToEndGoal.lean
'
date -u '+finished_utc=%Y-%m-%dT%H:%M:%SZ'
