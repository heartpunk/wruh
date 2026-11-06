#!/usr/bin/env bash
set -euo pipefail

: "${SHARD_INDEX:?}" "${SHARD_COUNT:?}"
root="$PWD"
results="$root/native-pbt-results"
work="${RUNNER_TEMP:-$results}/wruh-native-pbt-$SHARD_INDEX"
mkdir -p "$results/replay" "$work"
revision="${WRUH_SOURCE_REVISION:-$(git rev-parse HEAD)}"
[[ "$revision" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid source revision' >&2; exit 1; }
nix_bin="$(command -v nix)"

# Keep the XED version and build procedure identical to the catalogue.
nix-shell tools/iform_catalogue/shell.nix --run \
  "cc -O2 -Wall -Wextra -I\"\$XED_ROOT/include\" tools/iform_catalogue/xed_decode.c \"\$XED_ROOT/lib/libxed.a\" -o '$work/xed-decode'"
nix develop --no-write-lock-file --command bazel build --jobs=2 \
  //corpus:native_step_runner //extractor:native_catalogue_campaign
runner="$(readlink -f bazel-bin/corpus/native_step_runner)"
bwrap_root="$(nix build --no-link --print-out-paths 'github:NixOS/nixpkgs/e79d204daf01f8a877f7b2ce7324874ce9c84676#bubblewrap')"
bwrap="$(readlink -f "$bwrap_root/bin/bwrap")"

# Ubuntu 24.04 restricts user-namespace capabilities for unconfined
# executables. Permit them only for this exact immutable bubblewrap binary;
# leave the global restriction enabled and remove the temporary profile.
if [[ -r /proc/sys/kernel/apparmor_restrict_unprivileged_userns ]] &&
   [[ "$(cat /proc/sys/kernel/apparmor_restrict_unprivileged_userns)" == 1 ]]; then
  profile="$results/bwrap.apparmor"
  cat > "$profile" <<EOF
abi <abi/4.0>,
include <tunables/global>
profile wruh-native-pbt-bwrap "$bwrap" flags=(unconfined) {
  userns,
}
EOF
  sudo apparmor_parser -r "$profile"
  trap 'sudo apparmor_parser -R "$profile" || echo "Failed to unload temporary AppArmor profile" >&2' EXIT
fi
mapfile -t runtimes < <(ldd "$runner" | grep -oE '/nix/store/[^/[:space:]]+' | sort -u)
if (( ${#runtimes[@]} == 0 )); then
  echo 'No Nix runtime closure found for native runner' >&2
  exit 1
fi
runtime_args=()
for runtime in "${runtimes[@]}"; do runtime_args+=(--runtime "$runtime"); done
slice_args=()
if [[ -n "${WRUH_SYSTEMD_SLICE:-}" ]]; then slice_args+=(--slice="$WRUH_SYSTEMD_SLICE"); fi

# The runner independently verifies these cgroup limits and bubblewrap setup.
# A failed isolation setup is an ERROR; no unsandboxed fallback is permitted.
set +e
sudo systemd-run --quiet --wait --pipe --collect \
  "${slice_args[@]}" \
  --unit="wruh-native-pbt-${GITHUB_RUN_ID:-local}-${SHARD_INDEX}" \
  --uid="$(id -u)" --working-directory="$root" \
  --property=MemoryMax=6G --property=MemorySwapMax=0 \
  --property=CPUQuota=200% --property=TasksMax=512 \
  --setenv="HOME=$HOME" --setenv="PATH=$PATH" \
  --setenv="HYPOTHESIS_STORAGE_DIRECTORY=$results/replay" \
  "$nix_bin" develop --no-write-lock-file --command python -m extractor.native_catalogue_campaign \
    data/iform-catalogue/catalogue.jsonl --xed "$work/xed-decode" \
    --bwrap "$bwrap" --runner "$runner" "${runtime_args[@]}" \
    --source-revision "$revision" --examples 4 --row-seconds 30 \
    --shard-index "$SHARD_INDEX" --shard-count "$SHARD_COUNT" \
    2>&1 | tee "$results/campaign.log"
pipeline_status=("${PIPESTATUS[@]}")
status=${pipeline_status[0]}
if (( pipeline_status[1] != 0 )); then status=1; fi
set -e
if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  {
    echo "### Native PBT shard $SHARD_INDEX / $SHARD_COUNT"
    echo '```text'
    grep '^SUMMARY ' "$results/campaign.log" || echo 'Campaign did not produce a summary.'
    echo '```'
    echo 'Incomplete rows are coverage gaps, not matches; full reasons and witnesses are in the shard artifact.'
    echo '```text'
    awk '/^INCOMPLETE / && ++count <= 10 {print substr($0, 1, 500)}' "$results/campaign.log"
    echo '```'
  } >> "$GITHUB_STEP_SUMMARY"
fi
exit "$status"
