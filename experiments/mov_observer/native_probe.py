"""Hardware PBT of the exact MOV fragment, under an external ptrace supervisor.

The supervisor and kernel ABI are explicit calibration dependencies. They are
not part of the MOV-only fragment and are not proved by the fragment's AYXG
theorems. No tested instruction is compiled from this Python code.
"""
import ctypes as C
import os
from pathlib import Path
import signal
import struct
import sys

from hypothesis import given, settings, seed, strategies as st
from hypothesis.database import DirectoryBasedExampleDatabase
from stub import CODE, DATA, DATA_SIZE, GPRS, RECORD, RECORD_SIZE, stub_bytes, write_artifacts
from extract_stub import extract, amd, z3

LIBC = C.CDLL(None, use_errno=True)
LIBC.ptrace.restype = C.c_long
LIBC.ptrace.argtypes = [C.c_uint, C.c_uint, C.c_void_p, C.c_void_p]
MASK = 2**64 - 1
FLAGS = (0, 2, 4, 6, 7, 10, 11)
FP_MASK_OBSERVATIONS = set()
FIELDS = ("r15", "r14", "r13", "r12", "rbp", "rbx", "r11", "r10", "r9", "r8",
          "rax", "rcx", "rdx", "rsi", "rdi", "orig_rax", "rip", "cs", "eflags",
          "rsp", "ss", "fs_base", "gs_base", "ds", "es", "fs", "gs")


class Registers(C.Structure):
    _fields_ = [(name, C.c_ulonglong) for name in FIELDS]


def ptrace(request, pid, address=0, data=0):
    C.set_errno(0)
    result = LIBC.ptrace(request, pid, address, data)
    error = C.get_errno()
    if result == -1 and error:
        raise OSError(error, os.strerror(error))
    return result


def getregs(pid):
    value = Registers()
    ptrace(12, pid, 0, C.byref(value))
    return value


def getfp(pid):
    value = (C.c_ubyte * 512)()
    ptrace(14, pid, 0, C.byref(value))
    return bytes(value)


def read_memory(pid, address, length):
    assert length % 8 == 0
    return b"".join(struct.pack("<Q", ptrace(2, pid, address + i) & MASK)
                    for i in range(0, length, 8))


def write_memory(pid, address, data):
    assert len(data) % 8 == 0
    for offset in range(0, len(data), 8):
        ptrace(5, pid, address + offset, int.from_bytes(data[offset:offset+8], "little"))


def snapshot(executable, values, flag_bits, memory, xmm):
    pid = os.fork()
    if pid == 0:
        try:
            LIBC.prctl(1, signal.SIGKILL, 0, 0, 0)  # die with supervisor
            ptrace(0, 0)  # TRACEME; exec stops before the first target instruction
            os.execve(str(executable), [str(executable)], {})
        except BaseException:
            os._exit(127)
    try:
        waited, status = os.waitpid(pid, 0)
        assert waited == pid and os.WIFSTOPPED(status) and os.WSTOPSIG(status) == signal.SIGTRAP
        ptrace(0x4200, pid, 0, 0x00100000)  # SETOPTIONS, EXITKILL
        registers = getregs(pid)
        assert registers.rip == CODE
        for name, value in zip(GPRS, values):
            setattr(registers, name, value)
        registers.eflags = 0x202 | sum(((flag_bits >> i) & 1) << bit for i, bit in enumerate(FLAGS))
        registers.orig_rax = MASK  # kernel bookkeeping, not an architectural GPR
        ptrace(13, pid, 0, C.byref(registers))
        write_memory(pid, DATA, memory)
        fp = bytearray(getfp(pid))
        fp[160:416] = xmm
        fp_buffer = (C.c_ubyte * 512).from_buffer_copy(fp)
        ptrace(15, pid, 0, C.byref(fp_buffer))
        before = getregs(pid)
        before_fp = getfp(pid)
        assert getfp(pid) == before_fp, "FP capture changed without tracee execution"
        assert [getattr(before, name) for name in GPRS] == values
        assert before.eflags == registers.eflags
        assert before_fp[160:416] == xmm
        invariant_fields = (*GPRS, "eflags", "cs", "ss", "ds", "es", "fs", "gs", "fs_base", "gs_base")
        for index in range(len(GPRS)):
            ptrace(9, pid)  # SINGLESTEP; no stop instruction in the fragment
            waited, status = os.waitpid(pid, 0)
            assert waited == pid and os.WIFSTOPPED(status) and os.WSTOPSIG(status) == signal.SIGTRAP
            info = (C.c_byte * 128)()
            ptrace(0x4202, pid, 0, C.byref(info))
            assert struct.unpack_from("<i", bytes(info), 8)[0] == 2, "not TRAP_TRACE"
            after = getregs(pid)
            assert after.rip == CODE + 7 * (index + 1)
            differences = {name: (getattr(before, name), getattr(after, name))
                           for name in invariant_fields
                           if getattr(before, name) != getattr(after, name)}
            assert not differences, (index, differences)
        after_fp = getfp(pid)
        # Intel SDM vol. 1, section 11.6.6: bytes 28..31 are MXCSR_MASK,
        # a capability mask in the save image, not the MXCSR register.
        # Preserve this metadata separately. MXCSR itself (24..27), every
        # x87 field, and all XMM registers remain in the state comparison.
        # Reserved padding in the x87 slots and tail is not register state.
        mask_pair = (int.from_bytes(before_fp[28:32], "little"),
                     int.from_bytes(after_fp[28:32], "little"))
        if mask_pair not in FP_MASK_OBSERVATIONS:
            FP_MASK_OBSERVATIONS.add(mask_pair)
            label = f"fp-mask-{mask_pair[0]:08x}-{mask_pair[1]:08x}"
            evidence = Path(os.environ["MOV_OBSERVER_OUT"])
            (evidence / f"{label}-before.bin").write_bytes(before_fp)
            (evidence / f"{label}-after.bin").write_bytes(after_fp)
            print(f"MXCSR_MASK metadata: before={mask_pair[0]:#x}, after={mask_pair[1]:#x}; "
                  "raw records retained", flush=True)
        fp_offsets = list(range(5)) + list(range(6, 28))
        fp_offsets += [32 + 16*i + b for i in range(8) for b in range(10)]
        fp_offsets += list(range(160, 416))
        fp_differences = [i for i in fp_offsets if before_fp[i] != after_fp[i]]
        assert not fp_differences, ("FP/SIMD preservation", fp_differences)
        assert read_memory(pid, CODE, len(stub_bytes())) == stub_bytes()
        return read_memory(pid, DATA, DATA_SIZE)
    finally:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            os.waitpid(pid, 0)
        except ChildProcessError:
            pass


def observed_ok(observed, initial, values):
    offset = RECORD - DATA
    expected = b"".join(value.to_bytes(8, "little") for value in values)
    return (observed[offset:offset+RECORD_SIZE] == expected
            and observed[:offset] == initial[:offset]
            and observed[offset+RECORD_SIZE:] == initial[offset+RECORD_SIZE:])


def main():
    if sys.platform != "linux" or os.environ.get("WRUH_MOV_SANDBOX") != "1":
        raise RuntimeError("run only inside the bounded bubblewrap experiment")
    out = Path(os.environ["MOV_OBSERVER_OUT"])
    write_artifacts(out)
    _, expression, _ = extract()
    expressions = [z3.simplify(z3.Select(expression, z3.BitVecVal(RECORD+i, 64,
                       ctx=expression.ctx))) for i in range(RECORD_SIZE)]
    count = 0

    @seed(0x4D4F56)
    @settings(max_examples=200, deadline=None, print_blob=True,
              database=DirectoryBasedExampleDatabase(str(out / "hypothesis")))
    @given(st.lists(st.integers(0, MASK), min_size=16, max_size=16),
           st.integers(0, 127), st.binary(min_size=64, max_size=64),
           st.binary(min_size=256, max_size=256))
    def property_test(values, flags, pattern, xmm):
        nonlocal count
        initial = pattern * (DATA_SIZE // len(pattern))
        observed = snapshot(out / "observer.elf", values, flags, initial, xmm)
        assert observed_ok(observed, initial, values), "snapshot or memory frame failed"
        substitutions = [(amd.canonical_register(name), z3.BitVecVal(value, 64,
                          ctx=expression.ctx)) for name, value in zip(GPRS, values)]
        predicted = bytes(z3.simplify(z3.substitute(e, *substitutions)).as_long()
                          for e in expressions)
        offset = RECORD - DATA
        assert observed[offset:offset+RECORD_SIZE] == predicted, "extracted model/native mismatch"
        # Calibrate the comparator against both a corrupted record and an
        # otherwise-correct record accompanied by an unauthorized memory write.
        for corruption in (offset, 0, DATA_SIZE - 1):
            bad = bytearray(observed)
            bad[corruption] ^= 1
            assert not observed_ok(bytes(bad), initial, values)
        count += 1
        if count % 25 == 0:
            print(f"native cases passed: {count}", flush=True)

    property_test()
    print(f"PASS: {count} generated states; all 16 stores; GPR/flags/segment preservation; "
          "legacy FP/XMM preservation; 128 captured bytes; memory frame; "
          "fresh model/native agreement; comparator mutations rejected", flush=True)


if __name__ == "__main__":
    main()
