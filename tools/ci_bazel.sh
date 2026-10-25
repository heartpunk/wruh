#!/usr/bin/env bash
set -euo pipefail

if [[ $# -eq 0 ]]; then
  echo "usage: $0 <bazel command and arguments>" >&2
  exit 2
fi

bazel_command="$1"
shift

bazel_args=("$bazel_command")
if [[ -n "${BUILDBUDDY_ORG_API_KEY:-}" ]]; then
  echo "BuildBuddy remote cache and invocation links are enabled."
  bazel_args+=(--config=buildbuddy_ci)
  bazel_args+=("--remote_header=x-buildbuddy-api-key=$BUILDBUDDY_ORG_API_KEY")
else
  echo "BuildBuddy is not configured; running Bazel without the BuildBuddy profile."
fi
bazel_args+=("$@")

exec nix develop --no-write-lock-file --command bazel "${bazel_args[@]}"
