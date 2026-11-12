let
  pkgs = import (builtins.fetchTarball "https://github.com/NixOS/nixpkgs/archive/e79d204daf01f8a877f7b2ce7324874ce9c84676.tar.gz") {};
  # This source reports 0.2496 in its metadata; preserve its source unchanged.
  xed = pkgs.xed.overrideAttrs (old: {
    nativeBuildInputs = map (p:
      if (p.pname or "") == "mbuild"
      then p.overridePythonAttrs (_: { version = "0.2496"; })
      else p) old.nativeBuildInputs;
  });
in pkgs.mkShell {
  packages = [ pkgs.gcc xed (import ./python.nix { inherit pkgs; }) ];
  XED_ROOT = "${xed}";
}
