#!/usr/bin/env bash
set -euo pipefail
export PATH=/run/current-system/sw/bin
export PYTHONPATH=/nix/store/prgqrm74px43hwndnivs00ii41zlmllj-source/python
export RUNFILES_DIR=/tmp/wruh-mov-observer-20261106/out/runtime.runfiles
export GHOT_LIBSTDCXX_RLOCATION=lib/libstdc++.so.6
cd /home/heartpunk/workspaces/observer-shim-proof-65844e28/experiments/mov_observer/native_shim/proof
/nix/store/mv49y1qn55ifd106gyz92mrg6iqnjr6f-python3-3.12.15-env/bin/python3 extract.py out
