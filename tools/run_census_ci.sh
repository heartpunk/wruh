#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

target_id="${WRUH_CENSUS_TARGET_ID:?WRUH_CENSUS_TARGET_ID is required}"
report_dir="${RUNNER_TEMP:?RUNNER_TEMP is required}/wruh-census-$target_id"
mkdir -p "$report_dir"

bazel_version="$(nix develop --no-write-lock-file --command bazel --version)"
nix_version="$(nix --version)"

bazel_args=(test --nocache_test_results --test_timeout=21600 --nozip_undeclared_test_outputs)
test_args=(
  "--test_arg=--target-id=$target_id"
  "--test_arg=--binary-identifier=${WRUH_CENSUS_BINARY:?WRUH_CENSUS_BINARY is required}"
  "--test_arg=--target-kind=${WRUH_CENSUS_TARGET_KIND:-generic}"
  "--test_arg=--target-version=${WRUH_CENSUS_VERSION:?WRUH_CENSUS_VERSION is required}"
  "--test_arg=--target-platform=x86_64-linux"
  "--test_arg=--build-package=${WRUH_CENSUS_PACKAGE:?WRUH_CENSUS_PACKAGE is required}"
  "--test_arg=--build-configuration=${WRUH_CENSUS_CONFIGURATION:?WRUH_CENSUS_CONFIGURATION is required}"
  "--test_arg=--build-output=${WRUH_CENSUS_DERIVATION:?WRUH_CENSUS_DERIVATION is required}"
  "--test_arg=--nixpkgs-revision=${WRUH_CENSUS_NIXPKGS_REVISION:?WRUH_CENSUS_NIXPKGS_REVISION is required}"
  "--test_arg=--ayxg-revision=${WRUH_CENSUS_AYXG_REVISION:?WRUH_CENSUS_AYXG_REVISION is required}"
  "--test_arg=--wruh-revision=${GITHUB_SHA:?GITHUB_SHA is required}"
  "--test_arg=--bazel-version=$bazel_version"
  "--test_arg=--nix-version=$nix_version"
)
if [[ -n "${WRUH_CENSUS_TARGET_IMPLEMENTATION:-}" ]]; then
  test_args+=("--test_arg=--target-implementation=$WRUH_CENSUS_TARGET_IMPLEMENTATION")
fi
bazel_args+=("${test_args[@]}" //extractor:binary_census_remote_test)

test_status=0
bash tools/ci_bazel.sh "${bazel_args[@]}" || test_status=$?

# Bazel downloads TEST_UNDECLARED_OUTPUTS_DIR from the test action into this
# directory, including when the test fails after producing partial reports.
testlogs="$(nix develop --no-write-lock-file --command bazel info bazel-testlogs)"
test_outputs="$testlogs/extractor/binary_census_remote_test/test.outputs"
if [[ -d "$test_outputs" ]]; then
  cp -a "$test_outputs/." "$report_dir/"
elif [[ $test_status -eq 0 ]]; then
  echo "Bazel passed without materializing census test outputs at $test_outputs" >&2
  test_status=1
fi
if [[ $test_status -eq 0 && ! -f "$report_dir/summary.json" ]]; then
  echo "Bazel passed without producing summary.json in $report_dir" >&2
  test_status=1
fi

exit "$test_status"
