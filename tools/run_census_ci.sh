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

test_status=0
bash tools/ci_bazel.sh "${bazel_args[@]}" || test_status=$?

# Bazel materializes each remote TestRunner's undeclared outputs separately.
testlogs="$(nix develop --no-write-lock-file --command bazel info bazel-testlogs)"
for target_id in "${target_ids[@]}"; do
  test_outputs="$testlogs/extractor/binary_census_${target_id}_remote_test/test.outputs"
  target_report_dir="$report_root/$target_id"
  if [[ -d "$test_outputs" ]]; then
    cp -a "$test_outputs/." "$target_report_dir/"
  elif [[ $test_status -eq 0 ]]; then
    echo "Bazel passed without materializing $target_id census outputs at $test_outputs" >&2
    test_status=1
  fi
  if [[ $test_status -eq 0 && ! -f "$target_report_dir/summary.json" ]]; then
    echo "Bazel passed without producing $target_id summary.json in $target_report_dir" >&2
    test_status=1
  fi
done

exit "$test_status"
