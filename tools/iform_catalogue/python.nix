{ pkgs }:
let
  iced = pkgs.python312Packages.buildPythonPackage {
    pname = "iced-x86";
    version = "1.21.0";
    format = "wheel";
    src = pkgs.fetchurl {
      url = "https://files.pythonhosted.org/packages/5d/08/054cac5c4f435a243e423323783992c78c7c2f22cf2269fcca145b8423af/iced_x86-1.21.0-cp38-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl";
      sha256 = "489789377bfc1fe432bd2a8a5780c9f3e7c35be2e6133b0de5432cd901cad32c";
    };
    nativeBuildInputs = [ pkgs.autoPatchelfHook ];
    buildInputs = [ pkgs.stdenv.cc.cc.lib ];
    pythonImportsCheck = [ "iced_x86" ];
  };
in pkgs.python312.withPackages (ps: [ iced ps.hypothesis ps.pyld ps.rdflib ])
