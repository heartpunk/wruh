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
    ayxg = {
      url = "github:heartpunk/ayxg/9689144cf70c3923b9000a88473a65e408f0935b";
      inputs.ifrl.follows = "ifrl";
      inputs.lean4-nix.follows = "ifrl/lean4-nix";
      inputs.floatlib-src.follows = "floatlib-src";
    };
    floatlib-src = {
      url = "github:lean-dojo/FloatLib/1e83f09ed8c41a953cf8f93d26c210778177b94a";
      flake = false;
    };
    lake-mathlib-src = {
      url = "github:leanprover-community/mathlib4/5ed2965256430c3649e86755f9576b54eca72435";
      flake = false;
    };
    lake-plausible-src = {
      url = "github:leanprover-community/plausible/118aa17ee84656b8bd727fef7c458ee8c833385c";
      flake = false;
    };
    lake-leansearchclient-src = {
      url = "github:leanprover-community/LeanSearchClient/ddf04cf3949fa556442341e87d47f9f6e6074707";
      flake = false;
    };
    lake-importgraph-src = {
      url = "github:leanprover-community/import-graph/e928b72544873815af278d38681b31c0293588e3";
      flake = false;
    };
    lake-proofwidgets-src = {
      url = "github:leanprover-community/ProofWidgets4/106ff4fafc74ef4ac99d81dbf3ab399118f497a5";
      flake = false;
    };
    lake-aesop-src = {
      url = "github:leanprover-community/aesop/355695d523e41d0554926416cba2a2b3544fbbc9";
      flake = false;
    };
    lake-qq-src = {
      url = "github:leanprover-community/quote4/6a489d9af5d0c47e5b259e2e8bcdfc1811b5a259";
      flake = false;
    };
    lake-batteries-src = {
      url = "github:leanprover-community/batteries/f2effa3d803fda822b1f97b806c47cf2adfbcbc2";
      flake = false;
    };
    lake-cli-src = {
      url = "github:leanprover/lean4-cli/e92c9f15fdfacc8536f31cfb3b7ad26c3c8cd204";
      flake = false;
    };
  };

  outputs = { self, nixpkgs, angr-nix, ifrl, ayxg, floatlib-src
    , lake-mathlib-src, lake-plausible-src, lake-leansearchclient-src
    , lake-importgraph-src, lake-proofwidgets-src, lake-aesop-src, lake-qq-src
    , lake-batteries-src, lake-cli-src, ... }:
    let
      systems = [ "aarch64-darwin" "x86_64-linux" ];
      lean4Nix = ifrl.lib.lean4-nix;
      angrNix = ifrl.lib.angr-nix;
      bazelFor = pkgs: import (ifrl.outPath + "/nix/bazel.nix") { inherit pkgs; };
      lakeSources = [
        { name = "mathlib"; src = lake-mathlib-src; }
        { name = "plausible"; src = lake-plausible-src; }
        { name = "LeanSearchClient"; src = lake-leansearchclient-src; }
        { name = "importGraph"; src = lake-importgraph-src; }
        { name = "proofwidgets"; src = lake-proofwidgets-src; }
        { name = "aesop"; src = lake-aesop-src; }
        { name = "Qq"; src = lake-qq-src; }
        { name = "batteries"; src = lake-batteries-src; }
        { name = "Cli"; src = lake-cli-src; }
      ];
      environments = nixpkgs.lib.genAttrs systems (system:
        let
          pkgs = import nixpkgs {
            inherit system;
            overlays = [
              (lean4Nix.readToolchainFile {
                toolchain = ./lean-toolchain;
                binary = true;
              })
              angrNix.overlays.default
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
          bazel = bazelFor pkgs;
          # Keep the dependencies shared with IFRL and AYXG, using WRUH's
          # pinned toolchain. The broad IFRL contributor shell also supplies
          # a second Lean version and unrelated developer tools.
          sharedPackages = [
            python
            pkgs.bashInteractive
            pkgs.git
            bazel
            pkgs.lean
            pkgs.z3
          ];
          packages = sharedPackages ++ [
            pkgs.actionlint
            pkgs.basedpyright
            pkgs.buildifier
            pkgs.coreutils
            pkgs.findutils
            pkgs.gnugrep
            pkgs.jdk21_headless
            pkgs.ruff
            pkgs.stdenv.cc
            pkgs.zstd
          ];
          workerRuntime = if pkgs.stdenv.isLinux then pkgs.buildEnv {
            name = "ghot-reapi-worker-runtime";
            paths = [
              pkgs.python312
              pkgs.llvmPackages.clang
              pkgs.llvmPackages.lld
              pkgs.gperftools
            ];
            pathsToLink = [ "/bin" "/lib" ];
            ignoreCollisions = true;
          } else pkgs.emptyDirectory;
          environment = {
            JAVA_HOME = pkgs.jdk21_headless.home;
            GHOT_NIX_LIBSTDCXX_ROOT = pkgs.lib.optionalString pkgs.stdenv.isLinux "${pkgs.stdenv.cc.cc.lib}";
            GHOT_NIX_ANGR_ROOT = pkgs.lib.optionalString pkgs.stdenv.isLinux "${python}";
            GHOT_REAPI_WORKER_RUNTIME_ROOT = pkgs.lib.optionalString pkgs.stdenv.isLinux "${workerRuntime}";
            PYTHONNOUSERSITE = "1";
            PYTHONSAFEPATH = "1";
          };
          shellHook = "";
        in {
          inherit packages environment shellHook;
          shell = pkgs.mkShell ({
            inherit packages shellHook;
          } // environment);
          development = import ./nix/dev-environment.nix {
            inherit pkgs packages environment shellHook;
          };
          workspace = import ./nix/workspace.nix {
            inherit pkgs lakeSources;
            src = self;
            ayxgSrc = ayxg;
            floatlibSrc = floatlib-src;
          };
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
