#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo=$(cd -- "$root/../../.." && pwd)
work="$root/out/work"
mkdir -p "$work"
: "${BWRAP:=$(command -v bwrap)}"
for binary in trials fp-trials; do
"$BWRAP" --unshare-all --unshare-user --disable-userns --cap-drop ALL \
 --clearenv --new-session --die-with-parent \
 --ro-bind /nix/store /nix/store --ro-bind /run/current-system/sw /run/current-system/sw \
 --ro-bind "$repo" /repo --bind "$work" /out --proc /proc --dev /dev \
 --size 536870912 --tmpfs /tmp --chdir /out \
 --setenv PATH /run/current-system/sw/bin --setenv HOME /tmp --setenv LEAN_NUM_THREADS 1 \
 -- /repo/experiments/mov_observer/native_observer/out/"$binary" /repo/experiments/mov_observer/fixtures /out
done
