# Package the flake's tracked WRUH source as the image's workspace. Nix builds
# this from the clean flake source; host checkouts and Bazel output trees are
# never copied into /workspace.
{ pkgs, src }:
pkgs.runCommand "wruh-workspace" { } ''
  set -euo pipefail
  mkdir -p "$out/workspace"
  cp -R ${src}/. "$out/workspace/"
''
