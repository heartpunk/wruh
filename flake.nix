{
  description = "Wruh fresh handler extraction environment";

  inputs = {
    ifrl.url = "github:heartpunk/ifrl/8b2ebf5e623cd024c5afb818dcf9159b6c20d0c7";
    ayxg = {
      url = "github:heartpunk/ayxg/ada7c821a3d7610d9d3cd2d17cd2f1ab48537579";
      inputs.ifrl.follows = "ifrl";
    };
    nixpkgs.follows = "ifrl/nixpkgs";
  };

  outputs = { nixpkgs, ifrl, ayxg, ... }:
    let
      systems = [ "aarch64-darwin" "x86_64-linux" ];
    in {
      devShells = nixpkgs.lib.genAttrs systems (system:
        let pkgs = nixpkgs.legacyPackages.${system};
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
          JAVA_HOME = pkgs.jdk21_headless.home;
          GHOT_NIX_LIBSTDCXX_ROOT = pkgs.lib.optionalString pkgs.stdenv.isLinux "${pkgs.stdenv.cc.cc.lib}";
          GHOT_REAPI_WORKER_RUNTIME_ROOT = pkgs.lib.optionalString pkgs.stdenv.isLinux "/nix/store/v1g3lwbbarxyrdl4b6b2mgdgdx9b7v9q-ghot-reapi-worker-runtime";
          shellHook = ''
            # Use IFRL's shared Python environment after inherited hooks run.
            export PATH="${ifrl.packages.${system}.angr-python}/bin:$PATH"
          '' + pkgs.lib.optionalString pkgs.stdenv.isLinux ''
            # Keep the runtime available without shadowing the shared Lean toolchain.
            export PATH="$PATH:/nix/store/v1g3lwbbarxyrdl4b6b2mgdgdx9b7v9q-ghot-reapi-worker-runtime/bin"
          '';
          PYTHONNOUSERSITE = "1";
          PYTHONSAFEPATH = "1";
        };
      });
    };
}
