#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
image="${WRUH_IMAGE:-ghcr.io/heartpunk/wruh-dev:latest}"
# A full Git checkout is required: linked worktree .git pointers are not portable.
test -d .git
docker build --network=host --tag "$image" .
docker image inspect "$image" --format '{{.Size}} bytes'
# Verify a fresh container with no network or mounted host stack.
docker run --rm --network=none "$image" bash -euo pipefail -c '
  test "$(id -u)" != 0
  test -w /nix/store
  nix --version
  git rev-parse HEAD
  python3 -c "import angr, z3; assert angr.__version__.startswith("10.")"
  lean --version
  test -f .lake/build/lib/lean/Wruh/FreshExtraction.olean
  test -x .lake/build/bin/wruh-fresh
  lake build Wruh wruh-fresh
  python3 -m unittest discover -s tests -p test_cli_smoke.py -v
  # Exercise Nix writes as well as reads without needing network access.
  nix build --offline --impure --no-link --expr '''derivation {
    name = "wruh-container-smoke"; system = builtins.currentSystem;
    builder = "/bin/sh"; args = [ "-c" "echo usable > $out" ];
  }'''
'
if [ -n "${RUNNER_TEMP:-}" ]; then
  docker save "$image" | gzip > "$RUNNER_TEMP/wruh-dev.tar.gz"
fi
