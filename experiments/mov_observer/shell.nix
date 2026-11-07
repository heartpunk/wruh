{ system ? builtins.currentSystem }:
let
  project = builtins.getFlake (toString ../..);
  pkgs = project.inputs.nixpkgs.legacyPackages.${system};
  # Extend the pinned Angr interpreter, rather than mixing Python versions.
  python = project.inputs.ifrl.packages.${system}.angr-python.override (old: {
    extraLibs = old.extraLibs ++ [ pkgs.python312Packages.hypothesis ];
  });
in assert system == "x86_64-linux";
pkgs.mkShell {
  inputsFrom = [ project.devShells.${system}.default ];
  packages = [ python pkgs.bubblewrap ];
  shellHook = ''
    export PATH="${python}/bin:$PATH"
  '';
}
