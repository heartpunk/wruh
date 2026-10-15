#!/usr/bin/env bash
set -euo pipefail

WRUH_UID=$(id -u)
WRUH_GID=$(id -g)
export WRUH_UID WRUH_GID
docker compose config --quiet
nix build .#docker-image --out-link "$RUNNER_TEMP/wruh-image" --print-build-logs
docker load --input "$RUNNER_TEMP/wruh-image"
docker image inspect ghcr.io/heartpunk/wruh-dev:latest --format '{{.Size}} bytes'

# The image includes the checkout; no host Nix store, daemon, or Docker socket is mounted.
docker compose run --rm -T dev bash -euo pipefail -c '
  test -f /workspace/Wruh.lean
  test -f /workspace/lakefile.lean
  if command -v nix; then
    printf "%s\n" "Unexpected Nix executable in the runtime image." >&2
    exit 1
  fi
  test ! -e /nix/var/nix/daemon-socket/socket
  test "$(id -u)" != 0
  test -n "$JAVA_HOME"
  java -version
  bazel --version
  git --version
  python3 --version
  touch .wruh-container-owner-check
'
test "$(stat -c %u .wruh-container-owner-check)" = "$(id -u)"
rm .wruh-container-owner-check

# Preserve the image for Docker-only users to load.
cp -L "$RUNNER_TEMP/wruh-image" "$RUNNER_TEMP/wruh-dev.tar.gz"
