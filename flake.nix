{
  description = "Wruh fresh handler extraction environment";

  inputs = {
    ifrl = {
      url = "git+ssh://git@github.com/heartpunk/ifrl.git?ref=ci/wave-1&rev=5cca8cb3235ebe8288e43a254d05380b10189f37&allRefs=1";
      inputs.angr-nix.follows = "angr-nix";
    };
    nixpkgs.follows = "ifrl/nixpkgs";
    angr-nix = {
      url = "github:heartpunk/angr-nix/ca288bef3145174ae8385004e2cbcf6caabb9a76";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { nixpkgs, angr-nix, ifrl, ... }:
    let
      systems = [ "aarch64-darwin" "x86_64-linux" ];
    in {
      devShells = nixpkgs.lib.genAttrs systems (system:
        let pkgs = nixpkgs.legacyPackages.${system};
        in {
        default = pkgs.mkShell {
          inputsFrom = [ ifrl.devShells.${system}.default ];
          packages = [
            angr-nix.packages.${system}.default
            pkgs.git
            pkgs.jdk21_headless
            (if pkgs.stdenv.isLinux then pkgs.bazel_9 else pkgs.bazelisk)
          ];
          JAVA_HOME = pkgs.jdk21_headless.home;
          GHOT_NIX_LIBSTDCXX_ROOT = pkgs.lib.optionalString pkgs.stdenv.isLinux "${pkgs.stdenv.cc.cc.lib}";
          GHOT_REAPI_WORKER_RUNTIME_ROOT = pkgs.lib.optionalString pkgs.stdenv.isLinux "/nix/store/v1g3lwbbarxyrdl4b6b2mgdgdx9b7v9q-ghot-reapi-worker-runtime";
          shellHook = pkgs.lib.optionalString pkgs.stdenv.isLinux ''
            export PATH="/nix/store/v1g3lwbbarxyrdl4b6b2mgdgdx9b7v9q-ghot-reapi-worker-runtime/bin:$PATH"
          '';
          PYTHONNOUSERSITE = "1";
          PYTHONSAFEPATH = "1";
        };
      });
    };
}
