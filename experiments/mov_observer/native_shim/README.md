# Exact-byte Lean native memory-write experiment

Linux x86-64, Lean 4.34.0. Base source revision:
f0bfb1f4eb37ed5dc005d7ce550000b6dc92811d.

`MemoryWrite.lean` declares one borrowed-buffer `BaseIO UInt64` external function.
The pinned compiler emits:

```
uint64_t wruh_write_memory_once(uint32_t, uint64_t, lean_object*);
```

There is no runtime world argument or result allocation on the direct call path.
`write_memory.S` implements that ABI directly. It uses the pinned scalar-array
layout (size at offset 8; data at offset 24), builds two iovecs on a 32-byte stack
frame and invokes Linux x86-64 process_vm_writev syscall 311. The raw result bits
return in RAX: success count or negative errno. The shim does not retry, translate
errors, allocate, resume the target, or call runtime helpers. It borrows the Lean
ByteArray, and preserves ABI callee-saved registers and the stack pointer.
The extracted-model ABI/frame proof is now in `proof/`; its precise boundary
is described below. This is not yet a full native FFI refinement proof.

The assembled text is 65 bytes / 16 instructions / seven mnemonics:
mov, lea, xor, sub, add, syscall, ret. It has no relocations. Exact bytes and
linked disassembly are retained in evidence. SHA256:
318c587381ddd44658b17e8c40b4b80a857989da16581ec7aa546a4e157f982a.
Pinned lean.h SHA256:
982c731a1fbacc7688006f44f9f7af9d9e3e0247d310a728827f49e7f1466c13.
A compiler/runtime ABI change requires revalidation of this layout and call ABI.

## Native experiment

Probe.lean starts target.py as a child; the child allocates test memory and
stops itself with SIGSTOP. Lean confirms its stopped state, invokes the native
shim on three ranges, then resumes it. The independent Python oracle compares
the entire mapping against the expected result. Python is test setup/oracle,
not the memory-writing implementation. No hand-written C is used. MemoryWrite.c
is preserved compiler output documenting the ABI, not a replacement shim.

Successful test (NixOS, fleet-build.slice, 2 GiB/no swap/one CPU):
- Three ranges / 1,034 bytes, including unaligned starts/ends and a page crossing.
- Full 12,288-byte region comparison catches writes outside those ranges.
- Lean borrowed-input sizes and contents unchanged.
- Raw -EFAULT from address zero and zero-length successful return.
- Clean process cleanup and overall exit 0.

The exact build/run script, source hashes and resources are in evidence.
This is a native leaf experiment. It does not yet call through SparseMemoryImage,
map arbitrary requested addresses, implement full native GPR installation, or
prove MemoryWriteCorrect/FFI refinement. It introduces no retry/abort policy for
the application: the test asserts its expected outcomes only.

## Exact-byte ABI/frame proof

`proof/extract.py` extracts the exact committed 65 bytes at address 0x400000:
13 instructions before the syscall, the two-byte syscall boundary, and the
ADD/RET suffix. It asserts sizes, instruction counts, jump kinds, a single
unconstrained successor per modeled block, and no suffix stores. Every canonical
AYXG state field is retained. The syscall is deliberately not executed by the
extractor; `SyscallABI` supplies its kernel return/frame contract.

The exporter checks that the four ordered eight-byte write events expand to
exactly the 32 exported byte writes. In particular, it preserves the actual
memory expression at the ByteArray-size read, after the first two stores.
`SizeFieldSeparate` is the geometric separation needed to show that this read
still sees the original header. No preinstalled result or assumed frame
preservation substitutes for these proofs.

`ShimProof.lean` proves:
- `syscall_arguments`: syscall 311 and all argument registers, including the
  original PID bits, local/remote iovec pointers, counts of one and flags zero.
- `descriptor_byte_0` through `descriptor_byte_31`: exact descriptor contents,
  with the original size bytes under the stated separation condition.
- `prefix_stack_frame`: all memory outside the 32-byte stack frame is preserved.
- `shim_abi`: raw RAX return, RSP advanced by exactly eight bytes across RET,
  original saved return address, all fields outside the explicit clobber list
  preserved, and all memory outside that stack frame preserved.
- `shim_borrowed_buffer`: the borrowed object's 24-byte header and payload remain
  unchanged when disjoint from the stack frame.
- `prefix_available` / `suffix_available`: the actual guarded AYXG steps are
  enabled at the entry address and kernel resumption address respectively.

The clobber list includes caller-saved GPRs, RIP, arithmetic flags and memory;
RSP and memory receive the stronger specific conclusions above. Other modeled
fields, including callee-saved GPRs and FP/vector state, are preserved.

`SyscallABI` explicitly assumes the kernel returns raw RAX, resumes at the
suffix, preserves RSP and caller memory, and preserves fields outside the
listed clobbers. Caller-memory noninterference is a real assumption: a distinct
PID alone does not exclude shared-memory aliases. This proof does not establish
kernel progress, remote transfer correctness, or the compiler/runtime's FFI
refinement. It proves the shim ABI/frame behavior conditional on that kernel
contract and the extracted instruction semantics, as requested.

Run the existing `../check_pipeline.sh` through the pinned environment to check
these modules alongside the existing observer proofs. To regenerate, run
`python proof/extract.py OUTPUT_DIRECTORY` with the repository's pinned extraction
environment, then compare `OUTPUT_DIRECTORY/ShimModel.lean` byte-for-byte with
`proof/ShimModel.lean`. Extraction provenance and validation are in
`proof/evidence/`.
