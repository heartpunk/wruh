{
  description = "Wruh fresh handler extraction environment";

  inputs = {
    equanimity = {
      url = "github:heartpunk/equanimity/7312d503f84514f2a5b3c04769ba3eddd9d86411";
      flake = false;
    };
    ifrl.url = "github:heartpunk/ifrl/main";
    ayxg = {
      url = "github:heartpunk/ayxg/main";
      inputs.ifrl.follows = "ifrl";
    };
    nixpkgs.follows = "ifrl/nixpkgs";
  };

  outputs = { nixpkgs, ifrl, ayxg, equanimity, ... }:
    let
      systems = [ "aarch64-darwin" "x86_64-linux" ];
      ciPackages = nixpkgs.lib.genAttrs [ "x86_64-linux" ] (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          withSymbols = package: package.overrideAttrs (_: {
            dontStrip = true;
            stripAllList = [];
            stripDebugList = [];
          });
        in {
          apacheHttpdPinned = withSymbols pkgs.apacheHttpd;
        });
    in {
      packages = ciPackages;
      devShells = nixpkgs.lib.genAttrs systems (system:
        let pkgs = nixpkgs.legacyPackages.${system};
            buildbuddyRbe = pkgs.mkShell {
              packages = [
                ifrl.packages.${system}.angr-python
                pkgs.stdenv.cc.cc.lib
              ];
              GHOT_NIX_LIBSTDCXX_ROOT = pkgs.lib.optionalString (system == "x86_64-linux") "${pkgs.stdenv.cc.cc.lib}";
              shellHook = ''
                export PATH="${ifrl.packages.${system}.angr-python}/bin:$PATH"
                export PYTHONNOUSERSITE=1
                export PYTHONSAFEPATH=1
              '';
            };
        in {
        default = pkgs.mkShell {
          inputsFrom = [ ifrl.devShells.${system}.default ayxg.devShells.${system}.default ];
          packages = [
            ifrl.packages.${system}.angr-python
            pkgs.git
            pkgs.jdk21_headless
            (if pkgs.stdenv.isLinux then pkgs.bazel_9 else pkgs.bazelisk)
          ];
          IFRL_ANGR_ENVIRONMENT = "${ifrl.packages.${system}.angr-python}";
          GHOT_NIX_ANGR_ROOT = "${ifrl.packages.${system}.angr-python}";
          WRUH_AYXG_SOURCE = "${ayxg.outPath}";
          WRUH_EQUANIMITY_SOURCE = "${equanimity}";
          WRUH_ASPECTLIB_PATH = pkgs.python312.pkgs.makePythonPath [ pkgs.python312Packages.aspectlib ];
          JAVA_HOME = pkgs.jdk21_headless.home;
          GHOT_NIX_LIBSTDCXX_ROOT = pkgs.lib.optionalString pkgs.stdenv.isLinux "${pkgs.stdenv.cc.cc.lib}";
          GHOT_REAPI_WORKER_RUNTIME_ROOT = pkgs.lib.optionalString pkgs.stdenv.isLinux "/nix/store/v1g3lwbbarxyrdl4b6b2mgdgdx9b7v9q-ghot-reapi-worker-runtime";
          shellHook = ''
            # Use IFRL's shared Python environment after inherited hooks run.
            export PATH="${ifrl.packages.${system}.angr-python}/bin:$PATH"
            export PYTHONPATH="$PWD:${equanimity}:${ayxg.outPath}/python:$WRUH_ASPECTLIB_PATH''${PYTHONPATH:+:$PYTHONPATH}"
          '' + pkgs.lib.optionalString pkgs.stdenv.isLinux ''
            # Keep the runtime available without shadowing the shared Lean toolchain.
            export PATH="$PATH:/nix/store/v1g3lwbbarxyrdl4b6b2mgdgdx9b7v9q-ghot-reapi-worker-runtime/bin"
          '';
          PYTHONNOUSERSITE = "1";
          PYTHONSAFEPATH = "1";
        };
        } // (pkgs.lib.optionalAttrs (system == "x86_64-linux") {
          buildbuddyRbe = buildbuddyRbe;
        }));
    };
}
