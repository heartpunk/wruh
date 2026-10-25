#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

target_ids=(lua quickjs cpython apache node bun)
packages=(censusLua censusQuickjs censusCpython censusApache censusNode censusBun)
report_root="${RUNNER_TEMP:?RUNNER_TEMP is required}/wruh-census"
mkdir -p "$report_root"

# Keep the cache credential out of Nix builds and the later Bazel process.
cachix_auth_token="${CACHIX_AUTH_TOKEN:-}"
unset CACHIX_AUTH_TOKEN
cachix_push_enabled="${CACHIX_PUSH_ENABLED:-false}"
unset CACHIX_PUSH_ENABLED

# Nix stays on GitHub Actions. Each output becomes a declared Bazel input;
# the six census TestRunner actions are then submitted in one Bazel invocation.
repo_env_args=()
for index in "${!target_ids[@]}"; do
  target_id="${target_ids[$index]}"
  package="${packages[$index]}"
  target_output="$(nix build --no-link --no-write-lock-file --print-out-paths \
    ".#packages.x86_64-linux.$package")"
  if [[ "$target_output" != /nix/store/* || ! -d "$target_output" ]]; then
    echo "Nix returned an invalid census output for $target_id: $target_output" >&2
    exit 2
  fi
  if [[ "$cachix_push_enabled" == "true" ]]; then
    if [[ -z "$cachix_auth_token" ]]; then
      echo "CACHIX_AUTH_TOKEN is required to publish trusted census outputs." >&2
      exit 2
    fi
    echo "Publishing $target_id census output and runtime closure to Wruh Cachix."
    CACHIX_AUTH_TOKEN="$cachix_auth_token" cachix push wruh "$target_output"
  fi
  env_name="WRUH_CENSUS_${target_id^^}_OUTPUT"
  repo_env_args+=("--repo_env=$env_name=$target_output")
  mkdir -p "$report_root/$target_id"
done
unset cachix_auth_token

bazel_version="$(nix develop --no-write-lock-file --command bazel --version)"
nix_version="$(nix --version)"
testlogs="$(nix develop --no-write-lock-file --command bazel info bazel-testlogs)"

write_run_manifest() {
  local status="$1"
  local temporary="$report_root/run-manifest.json.tmp"
  local completed_targets=()
  for target_id in "${target_ids[@]}"; do
    if find "$report_root/$target_id" -name .collected -type f -print -quit 2>/dev/null | rg -q .; then
      completed_targets+=("$target_id")
    fi
  done
  python3 tools/write_census_run_manifest.py \
    --wruh-revision "$GITHUB_SHA" \
    --run-id "$WRUH_CI_RUN_ID" \
    --run-attempt "$WRUH_CI_RUN_ATTEMPT" \
    --requested-targets "${target_ids[@]}" \
    --collected-targets "${completed_targets[@]}" \
    --status "$status" >"$temporary"
  mv "$temporary" "$report_root/run-manifest.json"
}

collect_completed_outputs() {
  python3 tools/collect_census_outputs.py \
    --testlogs "$testlogs" \
    --report-root "$report_root" \
    --run-id "$WRUH_CI_RUN_ID" \
    --run-attempt "$WRUH_CI_RUN_ATTEMPT" \
    --checked-out-sha "$WRUH_CI_CHECKED_OUT_SHA"
}

write_run_manifest "running"
collector_pid=""
stop_collector() {
  if [[ -n "$collector_pid" ]]; then
    # The subshell may have a Python copy active. Let it notice Bazel's exit
    # and finish that copy before the final synchronous collection pass.
    wait "$collector_pid" 2>/dev/null || true
  fi
}
trap 'stop_collector; collect_completed_outputs; write_run_manifest incomplete' EXIT

bazel_args=(
  test
  --nocache_test_results
  --test_timeout=21600
  --nozip_undeclared_test_outputs
  --jobs=6
  "${repo_env_args[@]}"
  "--test_arg=--wruh-revision=${GITHUB_SHA:?GITHUB_SHA is required}"
  "--test_arg=--bazel-version=$bazel_version"
  "--test_arg=--nix-version=$nix_version"
  "--test_arg=--ci-server-url=${WRUH_CI_SERVER_URL:?WRUH_CI_SERVER_URL is required}"
  "--test_arg=--ci-repository=${WRUH_CI_REPOSITORY:?WRUH_CI_REPOSITORY is required}"
  "--test_arg=--ci-pull-request-number=${WRUH_CI_PULL_REQUEST_NUMBER:?WRUH_CI_PULL_REQUEST_NUMBER is required}"
  "--test_arg=--ci-pull-request-id=${WRUH_CI_PULL_REQUEST_ID:?WRUH_CI_PULL_REQUEST_ID is required}"
  "--test_arg=--ci-pull-request-head-repository=${WRUH_CI_PULL_REQUEST_HEAD_REPOSITORY:?WRUH_CI_PULL_REQUEST_HEAD_REPOSITORY is required}"
  "--test_arg=--ci-pull-request-head-sha=${WRUH_CI_PULL_REQUEST_HEAD_SHA:?WRUH_CI_PULL_REQUEST_HEAD_SHA is required}"
  "--test_arg=--ci-run-id=${WRUH_CI_RUN_ID:?WRUH_CI_RUN_ID is required}"
  "--test_arg=--ci-run-attempt=${WRUH_CI_RUN_ATTEMPT:?WRUH_CI_RUN_ATTEMPT is required}"
  "--test_arg=--ci-checked-out-sha=${WRUH_CI_CHECKED_OUT_SHA:?WRUH_CI_CHECKED_OUT_SHA is required}"
  "--test_arg=--ci-workflow=${WRUH_CI_WORKFLOW:?WRUH_CI_WORKFLOW is required}"
  "--test_arg=--ci-job=${WRUH_CI_JOB:?WRUH_CI_JOB is required}"
)
for target_id in "${target_ids[@]}"; do
  bazel_args+=("//extractor:binary_census_${target_id}_remote_test")
done

bash tools/ci_bazel.sh "${bazel_args[@]}" &
bazel_pid=$!
(
  while kill -0 "$bazel_pid" 2>/dev/null; do
    collect_completed_outputs
    sleep 15
  done
) &
collector_pid=$!
test_status=0
wait "$bazel_pid" || test_status=$?
stop_collector
collect_completed_outputs

for target_id in "${target_ids[@]}"; do
  if ! find "$report_root/$target_id" -name summary.json -type f -print -quit | rg -q .; then
    echo "No completed census summary was collected for $target_id" >&2
    if [[ $test_status -eq 0 ]]; then
      test_status=1
    fi
  fi
done

if [[ $test_status -eq 0 ]]; then
  write_run_manifest complete
else
  write_run_manifest incomplete
fi
trap - EXIT

exit "$test_status"
