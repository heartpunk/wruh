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
    pkgs.python312
  ];
} ''
  set -euo pipefail

  workspace="$out/workspace"
  mkdir -p "$workspace/.lake/packages/ayxg"
  cp -R ${src}/. "$workspace/"
  ayxg="$workspace/.lake/packages/ayxg"
  cp -R ${ayxgSrc}/. "$ayxg/"
  ${pkgs.lib.concatMapStrings stageLakeSource lakeSources}

  # Nix's pinned GitHub source trees have no Git checkout metadata. Keep Lake
  # from trying to delete and reclone them by overriding Git manifest entries
  # to their staged, revision-pinned source paths.
  chmod -R u+w "$workspace"
  python3 - "$ayxg" "$workspace" <<'PY'
import json
import pathlib
import sys

ayxg, wruh = map(pathlib.Path, sys.argv[1:])
manifest = json.loads((ayxg / "lake-manifest.json").read_text())
packages = [
    {
        "type": "path",
        "dir": f".lake/packages/{package['name']}",
        "name": package["name"],
        "manifestFile": package["manifestFile"],
        "inherited": package["inherited"],
        "configFile": package["configFile"],
    }
    for package in manifest["packages"]
    if package["type"] == "git"
]

for root, prefix in (
    (ayxg, ".lake/packages"),
    (wruh, ".lake/packages/ayxg/.lake/packages"),
):
    entries = [
        {**package, "dir": f"{prefix}/{package['name']}"}
        for package in packages
    ]
    overrides = {"version": manifest["version"], "packages": entries}
    path = root / ".lake" / "package-overrides.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(overrides, indent=2) + "\n")
PY

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
