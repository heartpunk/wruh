#!/usr/bin/env bash
set -euo pipefail

if [[ $# -eq 0 ]]; then
  echo "usage: $0 <bazel command and arguments>" >&2
  exit 2
fi

bazel_command="$1"
shift

bazel_args=("$bazel_command")
if [[ "${BUILDBUDDY_REQUIRE_REMOTE:-false}" == "true" && -z "${BUILDBUDDY_ORG_API_KEY:-}" ]]; then
  echo "BUILDBUDDY_ORG_API_KEY is required for this trusted CI run." >&2
  exit 2
fi

if [[ -n "${BUILDBUDDY_ORG_API_KEY:-}" ]]; then
  if [[ -z "${BUILDBUDDY_RBE_CONTAINER_IMAGE:-}" ]]; then
    if [[ "${BUILDBUDDY_REQUIRE_REMOTE:-false}" == "true" ]]; then
      echo "BUILDBUDDY_RBE_CONTAINER_IMAGE is required for remote census execution." >&2
      exit 2
    fi
    echo "BuildBuddy key is present but the remote runtime image is unavailable." >&2
    exit 2
  fi
  echo "BuildBuddy remote execution, cache, and invocation links are enabled."
  bazel_args+=(--config=buildbuddy_ci)
  bazel_args+=("--remote_header=x-buildbuddy-api-key=$BUILDBUDDY_ORG_API_KEY")
  bazel_args+=("--remote_default_exec_properties=container-image=docker://$BUILDBUDDY_RBE_CONTAINER_IMAGE")
else
  echo "BuildBuddy is not configured; running Bazel without the BuildBuddy profile."
fi
bazel_args+=("$@")

exec nix develop --no-write-lock-file --command bazel "${bazel_args[@]}"
