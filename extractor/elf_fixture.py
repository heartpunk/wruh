"""Compiler-free ELF fixture shared by extraction smoke tests."""
import struct

BASE = 0x400000
TEXT_OFFSET = 0x1000


def write_fixture(path, fixtures):
    """Write ELF64 headers, one RX segment, .text and a real symbol table.

    Encoding the fixed bytes directly avoids a compiler/linker dependency in
    the existing Python smoke command. No inventory or CFG data is supplied.
    """
    text = bytearray(b'\x90' * max(offset + len(code) for _, offset, code, _, _ in fixtures))
    strings = bytearray(b'\0')
    symbols = bytearray(24)  # required null symbol
    for name, offset, code, _, _ in fixtures:
        text[offset:offset + len(code)] = code
        name_offset = len(strings)
        strings.extend((name if isinstance(name, bytes) else name.encode()) + b'\0')
        symbols.extend(struct.pack('<IBBHQQ', name_offset, 0x12, 0, 1,
                                   BASE + TEXT_OFFSET + offset, len(code)))
    section_names = b'\0.text\0.symtab\0.strtab\0.shstrtab\0'
    sym_offset = (TEXT_OFFSET + len(text) + 7) & ~7
    str_offset = sym_offset + len(symbols)
    names_offset = str_offset + len(strings)
    sections_offset = (names_offset + len(section_names) + 7) & ~7
    raw = bytearray(sections_offset + 5 * 64)
    ident = b'\x7fELF\x02\x01\x01' + bytes(9)
    raw[:64] = struct.pack('<16sHHIQQQIHHHHHH', ident, 2, 62, 1,
                          BASE + TEXT_OFFSET, 64, sections_offset, 0,
                          64, 56, 1, 64, 5, 4)
    raw[64:120] = struct.pack('<IIQQQQQQ', 1, 5, 0, BASE, BASE,
                             TEXT_OFFSET + len(text), TEXT_OFFSET + len(text), 0x1000)
    raw[TEXT_OFFSET:TEXT_OFFSET + len(text)] = text
    raw[sym_offset:sym_offset + len(symbols)] = symbols
    raw[str_offset:str_offset + len(strings)] = strings
    raw[names_offset:names_offset + len(section_names)] = section_names
    sections = (
        (1, 1, 6, BASE + TEXT_OFFSET, TEXT_OFFSET, len(text), 0, 0, 16, 0),
        (7, 2, 0, 0, sym_offset, len(symbols), 3, 1, 8, 24),
        (15, 3, 0, 0, str_offset, len(strings), 0, 0, 1, 0),
        (23, 3, 0, 0, names_offset, len(section_names), 0, 0, 1, 0),
    )
    for index, section in enumerate(sections, 1):
        start = sections_offset + index * 64
        raw[start:start + 64] = struct.pack('<IIQQQQIIQQ', *section)
    path.write_bytes(raw)

