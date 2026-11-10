"""Independent native memory oracle for the Lean syscall shim, not runtime code."""
import ctypes
import mmap
import os
import signal
import sys

pages = mmap.mmap(-1, 3 * mmap.PAGESIZE)
base = ctypes.addressof(ctypes.c_char.from_buffer(pages))
initial = bytes((i * 17 + 91) % 256 for i in range(len(pages)))
pages[:] = initial
# Sparse writes include unaligned endpoints and a page-boundary crossing.
cases = [(3, b"abc"), (mmap.PAGESIZE - 3, b"1234567"),
         (2 * mmap.PAGESIZE + 17, bytes(range(256)) * 4)]
print(os.getpid(), flush=True)
for offset, data in cases:
    print(base + offset, flush=True)
os.kill(os.getpid(), signal.SIGSTOP)
assert sys.stdin.readline().strip() == "check"
expected = bytearray(initial)
for offset, data in cases:
    expected[offset:offset + len(data)] = data
assert pages[:] == expected, "requested bytes or surrounding frame differ"
print("PASS: 3 sparse ranges, 1034 bytes, full 12288-byte frame", flush=True)
