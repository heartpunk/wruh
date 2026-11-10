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
These are implementation claims to prove later, not a completed formal proof.

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
