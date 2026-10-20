{
  description = "Wruh fresh handler extraction environment";

  inputs = {
    ifrl.url = "github:heartpunk/ifrl/e8974a263d6784422e90b076e9a058a6737f4ef1";
    ayxg = {
      url = "github:heartpunk/ayxg/ee82ce56fe2f5e6c337f671c74b1ad9098890e9e";
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
            ifrl.lib.angr-nix.packages.${system}.default
            pkgs.git
            pkgs.jdk21_headless
            (if pkgs.stdenv.isLinux then pkgs.bazel_9 else pkgs.bazelisk)
          ];
          IFRL_ANGR_ENVIRONMENT = "${ifrl.lib.angr-nix.packages.${system}.default}";
          GHOT_NIX_ANGR_ROOT = "${ifrl.lib.angr-nix.packages.${system}.default}";
          WRUH_AYXG_SOURCE = "${ayxg.outPath}";
          JAVA_HOME = pkgs.jdk21_headless.home;
          GHOT_NIX_LIBSTDCXX_ROOT = pkgs.lib.optionalString pkgs.stdenv.isLinux "${pkgs.stdenv.cc.cc.lib}";
          GHOT_REAPI_WORKER_RUNTIME_ROOT = pkgs.lib.optionalString pkgs.stdenv.isLinux "/nix/store/v1g3lwbbarxyrdl4b6b2mgdgdx9b7v9q-ghot-reapi-worker-runtime";
          shellHook = ''
            # AYXG selects its own Python for solver checks. Extraction needs
            # IFRL's Angr environment after the inherited hooks have run.
            export PATH="${ifrl.lib.angr-nix.packages.${system}.default}/bin:$PATH"
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
