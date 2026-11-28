"""Small AMD64 ELF fixtures for static extraction contract checks."""
import struct
from pathlib import Path

from extractor.backend import Session
from extractor.instruction_inventory import Interval

PC = 0x400200


def elf_fixture(path, relocations=(), *, code=b"\xc3", extra_functions=(), import_size=8):
    """ET_DYN with one load segment, explicit sections, and dynamic relocations.

    Relocations are (offset within data, ELF type, symbol index, addend).
    Symbol 1 is undefined; symbol 2 names the RET instruction at 0x200.
    """
    raw = bytearray(0x1000)
    raw[:64] = struct.pack(
        "<16sHHIQQQIHHHHHH",
        b"\x7fELF\x02\x01\x01" + bytes(9),
        3,
        62,
        1,
        0x200,
        64,
        0x800,
        0,
        64,
        56,
        2,
        64,
        8,
        7,
    )
    raw[64:120] = struct.pack("<IIQQQQQQ", 1, 7, 0, 0, 0, len(raw), len(raw), 0x1000)
    raw[120:176] = struct.pack("<IIQQQQQQ", 2, 6, 0x600, 0x600, 0x600, 144, 144, 8)
    if not 0 < len(code) <= 0x100:
        raise ValueError("fixture code must fit before data")
    raw[0x200:0x200 + len(code)] = code
    raw[0x300:0x340] = bytes(range(0x80, 0xC0))
    for index, (offset, kind, symbol, addend) in enumerate(relocations):
        struct.pack_into(
            "<QQq",
            raw,
            0x400 + index * 24,
            0x300 + offset,
            (symbol << 32) | kind,
            addend,
        )
    sym_offset = 0xb00 if extra_functions else 0x500
    str_offset = 0xd00 if extra_functions else 0x580
    strings = bytearray(b"\0external\0fixture\0")
    symbols = [(1, 0x11, 0, 0, import_size), (10, 0x12, 1, 0x200, len(code))]
    for name, offset, size in extra_functions:
        symbols.append((len(strings), 0x12, 1, offset, size))
        strings.extend(name.encode() + b"\0")
    raw[str_offset:str_offset + len(strings)] = strings
    for n, (name, typ, section, offset, size) in enumerate(symbols, 1):
        struct.pack_into("<IBBHQQ", raw, sym_offset + n * 24, name, typ, 0, section, offset, size)
    dynamic = (
        (5, str_offset),
        (6, sym_offset),
        (7, 0x400),
        (8, len(relocations) * 24),
        (9, 24),
        (10, len(strings)),
        (11, 24),
        (0, 0),
        (0, 0),
    )
    for index, pair in enumerate(dynamic):
        struct.pack_into("<qQ", raw, 0x600 + index * 16, *pair)
    names = b"\0.text\0.data\0.rela.dyn\0.dynsym\0.dynstr\0.dynamic\0.shstrtab\0"
    raw[0x700 : 0x700 + len(names)] = names
    sections = (
        (".text", 1, 6, 0x200, len(code), 0, 0, 1, 0),
        (".data", 1, 3, 0x300, 64, 0, 0, 8, 0),
        (".rela.dyn", 4, 2, 0x400, len(relocations) * 24, 4, 0, 8, 24),
        (".dynsym", 11, 2, sym_offset, 24 * (1 + len(symbols)), 5, 1, 8, 24),
        (".dynstr", 3, 2, str_offset, len(strings), 0, 0, 1, 0),
        (".dynamic", 6, 3, 0x600, 144, 5, 0, 8, 16),
        (".shstrtab", 3, 0, 0x700, len(names), 0, 0, 1, 0),
    )
    for index, (name, kind, flags, offset, size, link, info, align, entry) in enumerate(
        sections, 1
    ):
        struct.pack_into(
            "<IIQQQQIIQQ",
            raw,
            0x800 + index * 64,
            names.index(name.encode()),
            kind,
            flags,
            offset if flags else 0,
            offset,
            size,
            link,
            info,
            align,
            entry,
        )
    path.write_bytes(raw)


def code_session(directory, code):
    path = Path(directory) / "instruction.so"
    elf_fixture(path, code=code)
    return Session.load(path)


def code_inventory(session, size):
    return session.inventory([Interval(0x400000, PC), Interval(PC + size, 0x401000)])
