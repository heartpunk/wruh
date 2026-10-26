{
  description = "Wruh fresh handler extraction environment";

  inputs = {
    ifrl.url = "github:heartpunk/ifrl/main";
    ayxg = {
      url = "github:heartpunk/ayxg/7fc4cfc94766c9e6f7a48089b42bcf7fc38ff20a";
      inputs.ifrl.follows = "ifrl";
    };
    nixpkgs.follows = "ifrl/nixpkgs";
  };

  outputs = { nixpkgs, ifrl, ayxg, ... }:
    let
      systems = [ "aarch64-darwin" "x86_64-linux" ];
      censusPackages = nixpkgs.lib.genAttrs [ "x86_64-linux" ] (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          withSymbols = package: package.overrideAttrs (_: {
            dontStrip = true;
            stripAllList = [];
            stripDebugList = [];
          });
          censusTarget = { packageName, package, binaryPattern, buildConfiguration }:
            let
              unstripped = withSymbols package;
              outputs = unstripped.outputs or [ "out" ];
              searchRoots = pkgs.lib.concatMapStringsSep " " (output:
                "'${builtins.toString (unstripped.${output})}'"
              ) outputs;
            in pkgs.runCommand "wruh-census-${packageName}" {} ''
              set -euo pipefail
              mkdir -p "$out"
              binary="$(find -L ${searchRoots} -type f -path '${binaryPattern}' -print -quit)"
              if [[ -z "$binary" ]]; then
                echo "could not locate ${binaryPattern} in ${packageName} outputs" >&2
                exit 1
              fi
              ln -s "$binary" "$out/binary"
              printf '%s\n' '${package.version}' > "$out/version"
              printf '%s\n' '${packageName}' > "$out/package"
              printf '%s\n' '${buildConfiguration}' > "$out/build-configuration"
              printf '%s\n' '${unstripped.drvPath}' > "$out/package-derivation"
            '';
        in {
          censusLua = censusTarget {
            packageName = "lua5_5";
            package = pkgs.lua5_5;
            binaryPattern = "*/lib/liblua.so*";
            buildConfiguration = "lua5_5 shared library, dontStrip=true";
          };
          censusQuickjs = censusTarget {
            packageName = "quickjs";
            package = pkgs.quickjs;
            binaryPattern = "*/bin/qjs";
            buildConfiguration = "QuickJS qjs executable, dontStrip=true";
          };
          censusCpython = censusTarget {
            packageName = "python312";
            package = pkgs.python312;
            binaryPattern = "*/lib/libpython3.12.so*";
            buildConfiguration = "CPython 3.12 shared library, dontStrip=true";
          };
          censusApache = censusTarget {
            packageName = "apache-httpd";
            package = pkgs.apacheHttpd;
            binaryPattern = "*/bin/httpd";
            buildConfiguration = "Apache HTTP Server httpd executable, dontStrip=true";
          };
          censusNode = censusTarget {
            packageName = "nodejs";
            package = pkgs.nodejs;
            binaryPattern = "*/bin/node";
            buildConfiguration = "Nixpkgs Node.js executable, dontStrip=true";
          };
          censusBun = censusTarget {
            packageName = "bun";
            package = pkgs.bun;
            binaryPattern = "*/bin/bun";
            buildConfiguration = "Nixpkgs Bun executable, dontStrip=true";
          };
        });
    in {
      packages = censusPackages;
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
        } // (pkgs.lib.optionalAttrs (system == "x86_64-linux") {
          buildbuddyRbe = buildbuddyRbe;
        }));
    };
}
