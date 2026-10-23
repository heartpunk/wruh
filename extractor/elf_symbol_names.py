"""Audit ELF symbol bytes before accepting CLE's decoded string identities."""
from pathlib import Path

from elftools.common.utils import parse_cstring_from_stream, struct_parse
from elftools.elf.dynamic import DynamicSegment
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection


class SymbolEncodingError(ValueError):
    """An ELF name cannot pass losslessly through the UTF-8 string provider."""


def validate_elf_symbol_encoding(path: Path, names: set[str] | None = None) -> None:
    """Reject loss at the loader boundary, not valid Unicode symbol spellings.

    Pyelftools decodes string tables with UTF-8 replacement and CLE retains
    that result. A string-only artifact cannot distinguish arbitrary ELF byte
    names after that replacement. Check raw bytes before accepting its names.
    Literal U+FFFD is valid UTF-8 and is deliberately accepted. When names
    are supplied, check all raw spellings decoding to those used names only.
    """
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        tables = [
            (section, section.stringtable["sh_offset"], section["sh_offset"],
             section["sh_entsize"])
            for section in elf.iter_sections()
            if isinstance(section, SymbolTableSection)
        ]
        # Stripped ELF images may expose dynsym only through PT_DYNAMIC.
        if not any(table["sh_type"] == "SHT_DYNSYM" for table, *_ in tables):
            for segment in elf.iter_segments():
                if isinstance(segment, DynamicSegment):
                    _, offset = segment.get_table_offset("DT_STRTAB")
                    _, symbols_offset = segment.get_table_offset("DT_SYMTAB")
                    if offset is not None and symbols_offset is not None:
                        tables.append((segment, offset, symbols_offset,
                                       elf.structs.Elf_Sym.sizeof()))
        for table, string_offset, symbols_offset, entry_size in tables:
            for index in range(table.num_symbols()):
                # DynamicSegment.iter_symbols() strictly decodes names before
                # yielding them. Read only the raw entry here, so an unrelated
                # invalid byte name cannot abort a scoped audit.
                symbol = struct_parse(elf.structs.Elf_Sym, stream,
                                      stream_pos=symbols_offset + index * entry_size)
                offset = string_offset + symbol["st_name"]
                raw = parse_cstring_from_stream(stream, stream_pos=offset)
                if raw is None:
                    raise SymbolEncodingError(f"unterminated ELF symbol name in {path} at {offset:#x}")
                if names is not None and raw.decode("utf-8", errors="replace") not in names:
                    continue
                try:
                    raw.decode("utf-8", errors="strict")
                except UnicodeDecodeError as error:
                    raise SymbolEncodingError(
                        f"ELF symbol name in {path} at {offset:#x} is not UTF-8 "
                        f"(bytes={raw.hex()}); CLE's replacement decoding would "
                        "lose its identity; byte-oriented names are not yet supported"
                    ) from error
