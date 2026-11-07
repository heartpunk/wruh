"""Exact bytes for a MOV-only, sixteen-GPR observation fragment.

No assembler, compiler, target stack, borrowed GPR, call, return, or trap
instruction occurs in this fragment. A separate supervisor supplies entry
and stops execution after the last store. This is a GPR capture core, not
a complete flags/vector observer or a claim about timing/cache transparency.
"""
from pathlib import Path
import hashlib
import struct

GPRS = ("rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi",
        "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15")
CODE = 0x400000
DATA = 0x600000
PAGE = 4096
DATA_SIZE = 3 * PAGE
RECORD = DATA + PAGE + 64
RECORD_SIZE = 8 * len(GPRS)
LOAD_CODE = CODE + 0x100
INPUT = RECORD + 0x100


def stub_bytes() -> bytes:
    """REX.W[+R] 89 /r: MOV qword ptr [RIP + disp32], GPR64.

    mod=00 and r/m=101 select RIP-relative addressing. REX.R supplies the
    high bit of the source register number. Every instruction is seven bytes.
    The independent decoder/extractor must confirm these choices.
    """
    out = bytearray()
    for reg in range(len(GPRS)):
        destination = RECORD + 8 * reg
        next_ip = CODE + len(out) + 7
        out += bytes((0x48 | ((reg >> 3) << 2), 0x89, ((reg & 7) << 3) | 5))
        out += struct.pack("<i", destination - next_ip)
    return bytes(out)


def loader_bytes() -> bytes:
    """The reverse MOV form installs the sixteen GPRs from private input slots."""
    out = bytearray()
    for reg in range(len(GPRS)):
        source = INPUT + 8 * reg
        next_ip = LOAD_CODE + len(out) + 7
        out += bytes((0x48 | ((reg >> 3) << 2), 0x8b, ((reg & 7) << 3) | 5))
        out += struct.pack("<i", source - next_ip)
    return bytes(out)


def elf_bytes() -> bytes:
    """Static ELF containing only the fragment and a private writable area.

    It has no normal exit path: the supervisor must stop at CODE+len(stub).
    Never run it directly. Native testing is inside bubblewrap and a bounded
    fleet-build cgroup. The loader/kernel protocol is outside the MOV proof.
    """
    code = stub_bytes()
    ident = b"\x7fELF\x02\x01\x01" + bytes(9)
    header = ident + struct.pack("<HHIQQQIHHHHHH", 2, 62, 1, CODE, 64, 0, 0,
                                64, 56, 2, 0, 0, 0)
    executable = struct.pack("<IIQQQQQQ", 1, 5, PAGE, CODE, CODE,
                             len(code), PAGE, PAGE)
    data = struct.pack("<IIQQQQQQ", 1, 6, 2 * PAGE, DATA, DATA,
                      DATA_SIZE, DATA_SIZE, PAGE)
    prefix = header + executable + data
    return (prefix + bytes(PAGE - len(prefix)) + code
            + bytes(PAGE - len(code)) + bytes(DATA_SIZE))


def write_artifacts(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "observer.bin").write_bytes(stub_bytes())
    executable = directory / "observer.elf"
    executable.write_bytes(elf_bytes())
    executable.chmod(0o700)
    (directory / "bytes.txt").write_text(
        f"SHA256 {hashlib.sha256(stub_bytes()).hexdigest()}\n"
        f"entry {CODE:#x}\nend {CODE + len(stub_bytes()):#x}\n"
        f"record [{RECORD:#x}, {RECORD + RECORD_SIZE:#x})\n"
        + "\n".join(f"{CODE + 7*i:08x}: {stub_bytes()[7*i:7*(i+1)].hex()}"
                     f"    mov [{RECORD + 8*i:#x}], {reg}"
                     for i, reg in enumerate(GPRS)) + "\n")


if __name__ == "__main__":
    import sys
    write_artifacts(Path(sys.argv[1] if len(sys.argv) > 1 else "out"))
