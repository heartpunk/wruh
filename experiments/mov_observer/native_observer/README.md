# Lean native instruction observer: first working path

`Observer.observe` installs sixteen requested GPRs, raw RFLAGS and a finite
nonoverlapping sparse memory image, executes one target instruction, and returns
GPRs, RFLAGS, RIP, all requested memory regions and the raw Linux register image.
The supervisor is Lean. Small assembly syscall leaves use the pinned Lean 4.34
ABI. There is no Python supervisor and no authored C implementation.

It reuses `../fixtures/loader.bin` and `observer.bin` (sixteen RIP-relative MOVs
each), plus `../native_shim/write_memory.S`. Linux ptrace installs flags and
controls single-stepping; the existing MOV loader installs GPRs. One target step
is followed by immediate kernel-register capture, then the MOV capture fragment.
The immediate post-target flags/RIP are retained before redirecting execution.
Fresh, privately allocated ByteArrays receive syscall output; borrowed input
arrays are not mutated. Normal completion kills and reaps the child and removes
its generated ELF. Unexpected stops and syscall/cleanup errors throw IO errors;
no retry policy has been added.

## Run on NixOS

With Lean 4.34 (`lean` and `leanc`) on PATH and bubblewrap available:

```sh
bash experiments/mov_observer/native_observer/build.sh
bash experiments/mov_observer/native_observer/run.sh
```

`BWRAP` can name the bubblewrap executable. Build outputs go under ignored `out/`.
The run uses the existing bubblewrap isolation pattern. Use the fleet reservation
and bounded child cgroup when running remotely. The exact successful invocation,
tool/source hashes, CPU profile, resource limits and output are in `evidence/`.
All source edits were local; execution used a Git-bearing NixOS snapshot.

## Ten concrete trials, not a PBT campaign

`Trials.lean` contains ten hand-selected inputs and expected observations:

| Instruction | Input/result inspected |
| --- | --- |
| `mov rax, rbx` | 42 copied into RAX |
| `add rax, rbx` | maximum unsigned value + 1 → zero, CF/ZF set |
| `adc rax, rbx` | 5 + 7 + carry → 13 |
| `sub rax, rbx` | 0 − 1 → maximum unsigned value, borrow/sign set |
| `xor rax, rax` | zero result, ZF set; undefined AF not compared |
| `shl rax, 1` | high/low endpoint bits → 2, CF/OF set; undefined AF not compared |
| `cmp rax, rbx` | equal operands set ZF without changing either operand |
| `cmovz rcx, rbx` | taken conditional move copies 99 |
| `mov rax, [rdi]` | unaligned cross-page load, DF retained |
| `mov [rdi], rax` | unaligned cross-page store |

These are from IXYK's existing `catalog/x86_64_top_100.json` families:
MOV (1), ADD (2), CMP (9), XOR (11), SUB (17), ADC (37), SHL (38), CMOVE (42).
Every trial checks all sixteen GPRs, defined flag bits, target endpoint, and all
1,034 requested bytes. Memory includes a 1,024-byte region crossing a page,
another disjoint range sharing a mapped page, and a distant region. The eight-byte
operand starts at 0x100000ffc and crosses into the next page. Expected values are
concrete, written out in the trials; no semantic-model execution is involved.

All ten passed inside bubblewrap on NixOS with native hardware-backed execution.
The final build/run exited 0; child cleanup was checked, and the work directory
was empty afterward. Technical and scope reviewers found no remaining blocker.
This is a smoke result, not a coverage or correctness proof.

## Current boundaries

- Linux AMD64; the fixed harness reserves [0x400000,0x401000) for code and
  [0x600000,0x603000) for input/capture storage. Requested ranges whose mapping
  pages intersect these are rejected, not silently dropped.
- Memory is not restricted to instruction operands or a fixed payload size.
  The caller supplies all ranges. ELF mapping and available memory impose native
  limits; the ELF program-header count limit is checked explicitly.
- The caller supplies one instruction encoding, 1–15 bytes. The supervisor always
  executes exactly one hardware single-step; it is not an instruction decoder.
- Requested flags must be installable through Linux's register interface;
  installation is read back and checked. No flags are silently normalized.
- FP, vectors and structured fault observations are the next stages. Faults now
  abort with the unexpected stop status rather than being called observations.
- The observer is executable, not end-to-end proved. Existing MOV and shim proofs
  are retained; this change adds no proof project or new PBT framework.
