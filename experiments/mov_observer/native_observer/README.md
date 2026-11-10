# Lean native instruction observer: first working path

`Observer.observeFallthrough` installs sixteen requested GPRs, raw RFLAGS and a
finite nonoverlapping sparse memory image, then runs naturally through:

```
MOV loader → target → direct JMP → MOV capture → designated INT3
```

The supervisor uses PTRACE_CONT, not PTRACE_SINGLESTEP. The caller selects a
single instruction that completes by fallthrough. This is the straight-line
execution path, not a control-transfer router or instruction decoder.

The existing `../fixtures/loader.bin` and `observer.bin` stay at their original
addresses, preserving their RIP-relative operands. A five-byte relative jump
after the variable-length target reaches the unchanged capture fragment.
`../native_shim/write_memory.S` still installs requested memory. The supervisor
is Lean with small assembly syscall leaves; no Python supervisor or authored C.

`Observation.gprs` comes from the MOV capture record. `terminalFlags` and
`rawTerminalRegisters` are explicitly the saved terminal context, not invented
post-target RIP/flags. MOV and JMP preserve the modeled flag component
(CF/PF/AF/ZF/SF/OF/DF/AC/ID). Raw transient/debug flags such as RF must not be
claimed to survive from the target through capture. The original target PC is
not independently sampled by this path. Conditional/indirect control transfers
need their own routing and observations later.

The terminal stop must be SIGTRAP with the exact expected RIP and an INT3-compatible
siginfo code. An earlier target trap is not accepted as completed capture.
Fresh private ByteArrays receive syscall output; borrowed inputs are not mutated.
Normal completion kills/reaps the child and removes the generated ELF. Errors
abort; no retry policy or structured fault observation was added.

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

## Twelve concrete trials, not a PBT campaign

`Trials.lean` contains twelve hand-selected inputs and expected observations:

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
| `pushfq` | requested 0x202 stored at the target stack; RSP decreases by eight |
| `rep movsb` | both bytes copied; RCX reaches zero; RSI/RDI advance by two |

The original ten cases are from IXYK's existing `catalog/x86_64_top_100.json` families:
MOV (1), ADD (2), CMP (9), XOR (11), SUB (17), ADC (37), SHL (38), CMOVE (42).
Every trial checks all sixteen GPRs, defined flag bits, terminal marker, and all
1,034 requested bytes. Memory includes a 1,024-byte region crossing a page,
another disjoint range sharing a mapped page, and a distant region. The eight-byte
operand starts at 0x100000ffc and crosses into the next page. Expected values are
concrete, written out in the trials; no semantic-model execution is involved.

All twelve passed inside bubblewrap on NixOS with KVM enabled. Before this fix,
the same two added cases failed under single-stepping: PUSHFQ wrote 0x302 and
REP MOVSB returned with RCX=1 after copying one byte. The executed reproductions
are retained in `evidence/single-step-reproductions.log`, from revision
2db135901ebfdecfb6bf58bdc9f46f5208735c7b. No output masking/repair hides these effects;
the fix removes injected single-stepping from execution.
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
- The caller supplies one fallthrough instruction encoding, 1–15 bytes. This
  path does not establish branch outcomes; reaching capture alone is not a
  general proof of the target control-flow route.
- Requested flags must be installable through Linux's register interface;
  installation is read back and checked. No flags are silently normalized.
- FP, vectors and structured fault observations are the next stages. Faults now
  abort with the unexpected stop status rather than being called observations.
- The observer is executable, not end-to-end proved. Existing MOV and shim proofs
  are retained; this change adds no proof project or new PBT framework.
