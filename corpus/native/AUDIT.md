# Prepared native harness — execution NOT authorized

Exact source: `harness.c` plus `../templates.c`, restricted entry calls to
`alias`, `overlap`, and `division`. Compile at O0 and O2 with the existing
pinned Clang and no builtin/inlining/vectorization settings. Binary hashes
and disassembly must be recorded before asking to execute; none compiled yet.

Input: five unsigned decimal values, each <= UINT32_MAX. Case 0..2;
word offsets 0..7. Eight aligned uint32_t words (32 bytes) initialized from
input. Alias accesses complete in-bounds words, including equal pointers;
overlap writes two bytes at byte offset 0..7. Division uses uint32_t-derived
unsigned operands, avoiding quotient overflow; zero divisor takes C's branch.
Output: return value and every storage byte. No input pointers, files,
network, subprocesses, allocation, or unbounded loops in candidate functions.
Libc parsing/output and loader are harness dependencies, outside extraction.

Proposed Linux sandbox: bubblewrap user/mount/PID/network namespaces;
read-only runtime closure and exact binary, no home/workspace mounts,
empty temporary directory, no network, no capabilities, no-new-privileges;
2-second process timeout, 256 MiB memory, no swap, one CPU, 64 tasks.
Check namespace support first. Do not silently downgrade sandboxing.

STS runner remains to be wired before end-to-end comparison. It must map
entry ABI/registers, initialized stack and storage, execute local edges
through return, and compare return + all storage bytes. This goal prepares
and audits the native side only; it does not claim differential execution.
