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
Normal completion kills/reaps the child and removes the generated ELF. Harness errors abort; no retry policy was added. See the fault API below.

## Run on NixOS

Use the repository flake environment (pinned Lean 4.34, binutils and bubblewrap):

```sh
nix develop .#nativeObserver --command bash experiments/mov_observer/native_observer/build.sh
nix develop .#nativeObserver --command bash experiments/mov_observer/native_observer/run.sh
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
- The supported target-fault cases are described below; other process outcomes
  and stops outside that boundary abort the observation.
- The observer is executable, not end-to-end proved. Existing MOV and shim proofs
  are retained; this change adds no proof project or new PBT framework.

## FP installation and capture

`Request.fp` optionally supplies the Linux x86-64 512-byte legacy FP image already
specified by `../LegacyFp.lean`. Existing GETFPREGS/SETFPREGS calls install/read it;
no new assembly is required. `Observation` retains `requestedFp`, `installedFp`,
and `terminalFp`. With no requested image, the actual initial FP state is still
read and returned. With an image, installation is read back and architectural
bytes must match. MXCSR_MASK and reserved/padding bytes remain in the raw record,
but are not falsely required to behave as mutable architectural state.

`FpTrials.lean` adds six concrete examples: FLD m64, FADD ST0/ST1, FSTP m80,
ADDSD, masked DIVSD by zero, and ADDSD with upward rounding. The x87 examples use
TOP=3 initially, logical ST slots and physical tag bits. They retain 80-bit
payloads without conversion to the model's narrower fpreg representation. SSE
examples check exact result bits, MXCSR and preservation of other architectural
FP bytes, including the upper half of XMM0. The x87 examples check ST0, TOP/tag,
exception status, control word and unaffected XMM/MXCSR; they do not assert every
x87 slot or instruction-updated pointer/condition field. Every example checks
GPRs, flags and all 1,024 requested memory bytes, including cross-page operands.

Both binaries built with Lean 4.34 and passed on NixOS inside bubblewrap: all
12 original cases and all six FP examples. Evidence, source hashes and the 18
raw FP images are retained in `evidence/fp/`. The bounded fleet job
`observer-fp-2.service` exited 0 with 119,812,096 bytes peak memory. No generated
ELFs remained after cleanup. The first build caught a record-update indentation
error, corrected locally before this successful run. `run.sh` now runs all four binaries.
These are concrete smoke observations, not exhaustive FP validation.

## Vector state

The full xstate option uses Linux GETREGSET/SETREGSET, preserving the raw standard
image and the actual returned iovec length. CPUID leaf 0xD supplies component
locations; XCR0 supplies OS-enabled components. XSTATE_BV controls whether a
component contains saved data or represents its architectural initial zeros.
Comparisons use decoded vector bytes rather than treating XSAVE metadata as
instruction effects. Both installed FP and xstate snapshots describe state after
all installation. A request can supply legacy FP or full xstate, not both.

`VectorTrials.lean` checks seven concrete cases assembled from `vector-cases.S`:
legacy PADDQ XMM (upper lanes preserved), VEX VPXOR YMM (upper lanes zeroed),
VPADDQ ZMM, VPADDQ into ZMM16 with merge and zero masks, VMOVDQU64 storing ZMM31
across a page, and KXORQ. Each compares all 32 ZMM registers and eight opmasks,
GPRs/flags, legacy nonvector FP state and all requested memory. The examples
require AVX2 plus OS-enabled AVX-512F/BW; unavailable features are an explicit
error, not a passing skipped case. On the SSE-only NixOS builder, use
`OBSERVER_TRIALS="trials fp-trials"` to run just the earlier suites.

The existing AVX-512 KVM guest uses Ubuntu with Determinate Nix. Source remains
local; compilation uses NixOS and the same committed flake. NixOS's existing
`fleet-builder-vm120-1` public signing key is trusted on the guest. Private key
material remains on NixOS. The realized `nativeObserver` environment is copied
as a signed binary cache with signature checking enabled. This avoids rebuilding
its approximately 5 GiB closure on the guest.

All seven vector cases passed on the AVX-512 guest, as did the twelve scalar and
six FP cases. The run used a 2688-byte standard xstate image, XCR0=255, and CPUID
component offsets 576/1088/1152/1664 for YMM-high/opmasks/ZMM-high/high16-ZMM.
The VM's QMP query reported KVM enabled and present. The guest run exited 0;
no generated target ELFs remained. `evidence/vector/` retains build/run logs,
CPU/runtime metadata and requested/installed/terminal images (including the FP
regression images). The copied environment passed recursive signature verification.

The native instructions ran in the existing KVM guest, not emulation or on the
bare host. This is seven concrete smoke cases, not exhaustive vector validation.

## Fault observations

`observeInstruction` returns the same observation record with `fault = none` for
successful fallthrough, or `some TargetFault` for a supported synchronous fault.
The fault carries signal, code, optional address and raw 128-byte siginfo. The
address is absent for SI_KERNEL, whose union field is not guaranteed meaningful.
The raw register record retains saved restart RIP and RFLAGS, including hardware
RF. GPRs come directly from ptrace at the fault stop; the MOV capture is not run.
FP/xstate and every requested memory range are read while the child remains
stopped. Partial progress is preserved; no replay or automatic retry occurs.
`observeFallthrough` remains the strict success-only wrapper for existing callers.

The current boundary is SIGILL/SIGBUS/SIGFPE/SIGSEGV with a positive kernel code
and saved RIP exactly at the target instruction, excluding asynchronous
BUS_MCEERR_AO. External signals, setup/capture faults, other traps and arbitrary
control-transfer routes are not claimed as target-fault observations.

`FaultTrials.lean` exercises DIV by zero, an unmapped MOV load, UD2 and a partial
REP MOVSB store. The REP destination has one mapped byte at a page end: the first
copy survives, the next faults, RCX becomes one, and RSI/RDI advance by one.
A deliberately corrupted loader must raise a harness error rather than return a
target fault. Every case checks all GPRs, modeled flags, architectural FP fields,
requested memory and (on the capable guest) seeded extended-vector/mask state.

All four target-fault examples and the loader rejection passed on both NixOS and
the existing AVX-512 KVM guest. The full guest run also passed all twelve scalar,
six FP and seven vector examples: 29 target observations plus the negative
control. Evidence and raw fault snapshots are in `evidence/fault/`. Source was
edited locally, built using the flake on NixOS, and the same binaries transferred
to the guest. No target ELFs remained after cleanup. No proof or AYXG/native
semantic-comparison work was added.
