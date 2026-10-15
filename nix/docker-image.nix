# SPDX-FileCopyrightText: 2026 Sophie Smithburg
# SPDX-License-Identifier: GPL-3.0-or-later

{ pkgs, development, workspace }:
let
  entrypoint = pkgs.writeShellScript "wruh-container" ''
    set -euo pipefail
    uid=$(${pkgs.coreutils}/bin/id -u)
    gid=$(${pkgs.coreutils}/bin/id -g)
    {
      printf 'root:x:0:0:root:/tmp:/bin/sh\n'
      if [ "$uid" != 0 ]; then
        printf 'wruh:x:%s:%s:Developer:/tmp:/bin/sh\n' "$uid" "$gid"
      fi
    } > /run/wruh/passwd
    {
      printf 'root:x:0:\n'
      if [ "$gid" != 0 ]; then
        printf 'wruh:x:%s:\n' "$gid"
      fi
    } > /run/wruh/group
    exec ${development}/bin/wruh-dev "$@"
  '';
in
pkgs.dockerTools.buildLayeredImage {
  name = "ghcr.io/heartpunk/wruh-dev";
  tag = "latest";
  contents = [
    development
    workspace
    pkgs.cacert
    pkgs.dockerTools.binSh
    pkgs.dockerTools.usrBinEnv
    pkgs.dockerTools.fakeNss
  ];
  extraCommands = ''
    mkdir -p tmp run/wruh
    chmod 1777 tmp run/wruh
    chmod -R a+rwX workspace
    rm etc/passwd etc/group
    ln -s /run/wruh/passwd etc/passwd
    ln -s /run/wruh/group etc/group
  '';
  config = {
    Labels."org.opencontainers.image.source" = "https://github.com/heartpunk/wruh";
    Entrypoint = [ "${entrypoint}" ];
    WorkingDir = "/workspace";
    User = "1000:1000";
    Env = [
      "PATH=/bin"
      "HOME=/tmp"
      "SSL_CERT_FILE=${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt"
      "NIX_SSL_CERT_FILE=${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt"
    ];
  };
}
