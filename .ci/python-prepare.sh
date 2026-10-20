#!/usr/bin/env bash
set -euo pipefail
# The existing extractor imports the pinned AYXG Python package.
source_path=$(nix eval --raw --no-write-lock-file .#devShells.x86_64-linux.default.WRUH_AYXG_SOURCE)
printf 'PYTHONPATH=.:%s/python\n' "$source_path" >> "$GITHUB_ENV"
