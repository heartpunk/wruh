#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 5 ]]; then
  printf 'usage: %s CATALOGUE WORK_DIR OCCURRENCES SAMPLES_PER_OCCURRENCE SEED\n' "$0" >&2
  exit 2
fi

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
catalogue=$(realpath "$1")
mkdir -p "$2"
work=$(realpath "$2")
: "${WRUH_HEGEL_LIBRARY:?run through the Wruh Nix environment}"
: "${WRUH_ICED_PYTHON:?run through the Wruh Nix environment}"
: "${WRUH_AYXG_SOURCE:?run through the Wruh Nix environment}"
: "${GHOT_NIX_ANGR_ROOT:?run through the Wruh Nix environment}"

exec timeout "${WRUH_PBT_TIMEOUT_SECONDS:-300}" bwrap \
  --unshare-all --unshare-user --disable-userns --cap-drop ALL \
  --clearenv --new-session --die-with-parent \
  --ro-bind /nix/store /nix/store --ro-bind "$root" /repo \
  --ro-bind "$catalogue" /catalogue.jsonl --bind "$work" /out \
  --proc /proc --dev /dev --tmpfs /tmp --chdir /repo \
  --setenv PATH "$PATH" --setenv HOME /tmp \
  --setenv USER "${USER:-wruh}" --setenv LOGNAME "${USER:-wruh}" \
  --setenv WRUH_HEGEL_LIBRARY "$WRUH_HEGEL_LIBRARY" \
  --setenv WRUH_ICED_PYTHON "$WRUH_ICED_PYTHON" \
  --setenv WRUH_AYXG_SOURCE "$WRUH_AYXG_SOURCE" \
  --setenv GHOT_NIX_ANGR_ROOT "$GHOT_NIX_ANGR_ROOT" \
  --setenv PYTHONPATH "/repo:$WRUH_AYXG_SOURCE/python" \
  --setenv PYTHONNOUSERSITE 1 --setenv LEAN_NUM_THREADS 1 \
  -- /repo/.lake/build/bin/wruh-iform-pbt /catalogue.jsonl \
  /repo/experiments/iform_pbt/build_stub.sh /repo/.lake/build/bin/wruh-fresh \
  /repo/experiments/iform_pbt/metadata.py /repo/experiments/mov_observer/fixtures \
  /out "$3" "$4" "$5"
