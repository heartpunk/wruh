#!/usr/bin/env bash
set -euo pipefail
export PATH=/nix/store/qpk7v7b4ixkpa4jfsvgmmsmdr4l23in1-lean/bin:/nix/store/9nmzd62x45ayp4vmswvn6z45h6bzrsla-binutils-2.44/bin:/run/current-system/sw/bin
export LEAN_NUM_THREADS=1
cd /home/heartpunk/workspaces/observer-shim-f0bfb1f4/experiments/mov_observer/native_shim
export LEAN_PATH=.
lean --version
sha256sum MemoryWrite.lean Probe.lean write_memory.S target.py
lean -o MemoryWrite.olean -c MemoryWrite.c MemoryWrite.lean
lean -o Probe.olean -c Probe.c Probe.lean
leanc -O2 MemoryWrite.c Probe.c write_memory.S -o probe
leanc -c write_memory.S -o write_memory.o
objcopy -O binary --only-section=.text write_memory.o shim.bin
objdump -dr write_memory.o
sha256sum shim.bin
objdump --disassemble=wruh_write_memory_once probe > linked-disassembly.txt
readelf -r write_memory.o > relocations.txt
cp /nix/store/qpk7v7b4ixkpa4jfsvgmmsmdr4l23in1-lean/include/lean/lean.h lean-abi.h
sha256sum lean-abi.h
./probe /nix/store/1wbgna3xlprfllr1ysgpy9xiz0rxzglz-python3-3.12.15/bin/python3 target.py
