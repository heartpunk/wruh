#!/usr/bin/env bash
set -euo pipefail
export PATH=/nix/var/nix/profiles/default/bin:/usr/bin:/bin
cd /home/ubuntu/workspaces/wruh-vector-observer
nix --version
nix develop .#nativeObserver --command bash experiments/mov_observer/native_observer/run.sh
