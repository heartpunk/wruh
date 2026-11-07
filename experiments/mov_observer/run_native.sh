#!/usr/bin/env bash
set -euo pipefail
task_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "$task_root/../.." && pwd)
cd "$task_root"
mkdir -p out
: "${WRUH_AYXG_SOURCE:?Run in this experiment's shell.nix}"
: "${GHOT_NIX_LIBSTDCXX_ROOT:?Run in this experiment's shell.nix}"
export PYTHONPATH="$task_root:$repo_root:$WRUH_AYXG_SOURCE/python"
python3 extract_stub.py out | tee out/extraction.log
python3 extract_loader.py out | tee out/loader-extraction.log
python3 emit_pipeline.py out/Pipeline.lean
for model in Extracted InputModel; do
  cmp "models/$model.lean" "out/$model.lean"
done
cmp Pipeline.lean out/Pipeline.lean
cmp fixtures/observer.bin out/observer.bin
cmp fixtures/loader.bin out/loader.bin
BWRAP=$(command -v bwrap)
PYTHON_BIN=$(command -v python3)
mkdir -p out/runtime.runfiles/lib
ln -sfn "$GHOT_NIX_LIBSTDCXX_ROOT/lib/libstdc++.so.6" out/runtime.runfiles/lib/libstdc++.so.6
printf '%s\n' "python=$PYTHON_BIN" "bubblewrap=$BWRAP" \
  "ayxg=$WRUH_AYXG_SOURCE" "floatlib=$AYXG_FLOATLIB_SOURCE" > out/runtime.txt
cat /proc/cpuinfo > out/cpuinfo.txt
"$BWRAP" --unshare-all --unshare-user --disable-userns --cap-drop ALL \
  --clearenv --new-session --die-with-parent \
  --ro-bind /nix/store /nix/store --ro-bind "$repo_root" /repo \
  --bind "$task_root/out" /out --proc /proc --dev /dev --size 536870912 --tmpfs /tmp \
  --chdir /repo/experiments/mov_observer --setenv LANG C.UTF-8 \
  --setenv USER observer --setenv LOGNAME observer --setenv HOME /tmp \
  --setenv XDG_CACHE_HOME /tmp/cache --setenv PATH "$PATH" \
  --setenv WRUH_MOV_SANDBOX 1 --setenv MOV_OBSERVER_OUT /out \
  --setenv PYTHONNOUSERSITE 1 --setenv PYTHONSAFEPATH 1 \
  --setenv GHOT_NIX_LIBSTDCXX_ROOT "$GHOT_NIX_LIBSTDCXX_ROOT" \
  --setenv RUNFILES_DIR /out/runtime.runfiles \
  --setenv GHOT_LIBSTDCXX_RLOCATION lib/libstdc++.so.6 \
  --setenv PYTHONPATH "/repo/experiments/mov_observer:/repo:$WRUH_AYXG_SOURCE/python" \
  -- "$PYTHON_BIN" /repo/experiments/mov_observer/native_probe.py | tee out/native-pbt.log
