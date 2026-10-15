# Build WRUH and its pinned AYXG dependency inside a clean WRUH source tree.
# All Lake sources are explicit flake inputs, so this derivation builds offline
# and never imports a host checkout's .lake or Bazel output directories.
{ pkgs, src, ayxgSrc, floatlibSrc, lakeSources }:
let
  floatlib = pkgs.applyPatches {
    name = "floatlib-ayxg-scoped";
    src = floatlibSrc;
    patches = [ "${ayxgSrc}/nix/floatlib-smt-rna.patch" ];
  };
  stageLakeSource = { name, src }: ''
    mkdir -p "$ayxg/.lake/packages/${name}"
    cp -R ${src}/. "$ayxg/.lake/packages/${name}/"
  '';
in
pkgs.runCommand "wruh-workspace" {
  nativeBuildInputs = [
    pkgs.coreutils
    pkgs.findutils
    pkgs.git
    pkgs.lean
  ];
} ''
  set -euo pipefail

  workspace="$out/workspace"
  mkdir -p "$workspace/.lake/packages/ayxg"
  cp -R ${src}/. "$workspace/"
  ayxg="$workspace/.lake/packages/ayxg"
  cp -R ${ayxgSrc}/. "$ayxg/"
  ${pkgs.lib.concatMapStrings stageLakeSource lakeSources}

  export PATH="${pkgs.lib.makeBinPath [ pkgs.lean pkgs.coreutils pkgs.git ]}:$PATH"
  export WRUH_AYXG_SOURCE="$ayxg"
  export AYXG_FLOATLIB_SOURCE="${floatlib}"
  export AYXG_FLOATLIB_SOURCE_KEY="222236f04b51cfbf170bd4894542c9ac97436b15"
  jobs="''${NIX_BUILD_CORES:-1}"

  cd "$ayxg"
  lake -Kjobs="$jobs" build
  cd "$workspace"
  lake -Kjobs="$jobs" build
''
