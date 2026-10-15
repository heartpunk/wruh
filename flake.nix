{
  description = "Wruh fresh handler extraction environment";

  inputs = {
    ifrl = {
      url = "git+ssh://git@github.com/heartpunk/ifrl.git?ref=main";
      inputs.angr-nix.follows = "angr-nix";
    };
    nixpkgs.follows = "ifrl/nixpkgs";
    angr-nix = {
      url = "github:heartpunk/angr-nix/ca288bef3145174ae8385004e2cbcf6caabb9a76";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, angr-nix, ifrl, ... }:
    let
      systems = [ "aarch64-darwin" "x86_64-linux" ];
      lean4Nix = ifrl.lib.lean4-nix;
      environments = nixpkgs.lib.genAttrs systems (system:
        let
          pkgs = import nixpkgs {
            inherit system;
            overlays = [
              (lean4Nix.readToolchainFile {
                toolchain = ./lean-toolchain;
                binary = true;
              })
              angr-nix.overlays.default
              (final: prev: {
                python312 = prev.python312.override (old: {
                  packageOverrides = nixpkgs.lib.composeExtensions
                    (old.packageOverrides or (_: _: { }))
                    (pyFinal: pyPrev: {
                      angr = pyPrev.angr.overridePythonAttrs (attrs: {
                        # The prebuilt Darwin wheel has no Mach-O header padding
                        # for the absolute Nix-store Z3 path.
                        preFixup = if final.stdenv.isDarwin then ''
                          angrSitePackages="$out/${pyPrev.python.sitePackages}/angr"
                          ln -s "${pyPrev.z3-solver}/${pyPrev.python.sitePackages}/z3/lib/libz3.dylib" \
                            "$angrSitePackages/a"
                          install_name_tool -change libz3.dylib @loader_path/a \
                            "$angrSitePackages/rustylib.abi3.so"
                        '' else (attrs.preFixup or "");
                      });
                    });
                });
              })
            ];
          };
          python = pkgs.python312.withPackages (ps: [
            ps.angr
            ps.coverage
            ps.hypothesis
            ps.ipykernel
            ps.pytest
            ps.unicorn
            ps.z3-solver
          ]);
          bazel = if pkgs.stdenv.isLinux then pkgs.bazel_9 else pkgs.bazelisk;
          packages = [
            python
            pkgs.actionlint
            pkgs.basedpyright
            pkgs.bashInteractive
            bazel
            pkgs.buildifier
            pkgs.coreutils
            pkgs.findutils
            pkgs.gnugrep
            pkgs.git
            pkgs.jdk21_headless
            pkgs.lean4
            pkgs.ruff
            pkgs.stdenv.cc
            pkgs.zstd
          ];
          environment = {
            JAVA_HOME = pkgs.jdk21_headless.home;
            GHOT_NIX_LIBSTDCXX_ROOT = pkgs.lib.optionalString pkgs.stdenv.isLinux "${pkgs.stdenv.cc.cc.lib}";
            GHOT_REAPI_WORKER_RUNTIME_ROOT = pkgs.lib.optionalString pkgs.stdenv.isLinux "/nix/store/v1g3lwbbarxyrdl4b6b2mgdgdx9b7v9q-ghot-reapi-worker-runtime";
            PYTHONNOUSERSITE = "1";
            PYTHONSAFEPATH = "1";
          };
          shellHook = pkgs.lib.optionalString pkgs.stdenv.isLinux ''
            export PATH="/nix/store/v1g3lwbbarxyrdl4b6b2mgdgdx9b7v9q-ghot-reapi-worker-runtime/bin:$PATH"
          '';
        in {
          inherit packages environment shellHook;
          shell = pkgs.mkShell ({
            inherit packages shellHook;
          } // environment);
          development = import ./nix/dev-environment.nix {
            inherit pkgs packages environment shellHook;
          };
          workspace = import ./nix/workspace.nix { inherit pkgs; src = self; };
        });
    in {
      devShells = nixpkgs.lib.mapAttrs (_: environment: {
        default = environment.shell;
      }) environments;
      packages = nixpkgs.lib.mapAttrs (system: environment: {
        default = environment.development;
        dev-environment = environment.development;
      } // nixpkgs.lib.optionalAttrs (system == "x86_64-linux") {
        docker-image = import ./nix/docker-image.nix {
          pkgs = nixpkgs.legacyPackages.${system};
          development = environment.development;
          workspace = environment.workspace;
        };
      }) environments;
    };
}
