# SPDX-FileCopyrightText: 2026 Sophie Smithburg
# SPDX-License-Identifier: GPL-3.0-or-later

{ pkgs, packages, environment, shellHook }:
let
  activation = pkgs.writeText "wruh-dev-env.sh" (
    pkgs.lib.concatStringsSep "\n" (pkgs.lib.mapAttrsToList
      (name: value: "export ${name}=${pkgs.lib.escapeShellArg value}") environment)
    + "\nexport PATH=${pkgs.lib.escapeShellArg (pkgs.lib.makeBinPath packages)}:\"$PATH\"\n"
    + shellHook
  );
  launcher = pkgs.writeShellScriptBin "wruh-dev" ''
    source ${activation}
    if [ "$#" -eq 0 ]; then
      exec ${pkgs.bashInteractive}/bin/bash --noprofile --norc
    fi
    exec "$@"
  '';
in
pkgs.buildEnv {
  name = "wruh-dev-environment";
  paths = packages ++ [ pkgs.bashInteractive launcher ];
  pathsToLink = [ "/bin" "/share" ];
  ignoreCollisions = true;
}
