"""Small real ELF images and explicit CLE extent boundary fixtures.

The ELF writer encodes the public ELF64 format, not a mocked loader. Fixtures
are data only: no native execution and no runtime resolver results are guessed.
"""

from __future__ import annotations

import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from extractor.native_runtime import preload_libstdcxx

preload_libstdcxx()
from cle.backends.elf.relocation.amd64 import R_X86_64_64, R_X86_64_COPY, R_X86_64_PC32
from cle.backends.elf.relocation.generic import GenericTLSDescriptorReloc
from cle.backends.relocation import Relocation
from extractor.loaded_image import (
    load_object_set,
    loaded_image_data,
    relocation_write_size,
)


def elf_fixture(path, relocations=()):
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
    raw[0x200] = 0xC3
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
    strings = b"\0external\0fixture\0"
    raw[0x580 : 0x580 + len(strings)] = strings
    struct.pack_into("<IBBHQQ", raw, 0x518, 1, 0x11, 0, 0, 0, 8)
    struct.pack_into("<IBBHQQ", raw, 0x530, 10, 0x12, 0, 1, 0x200, 1)
    dynamic = (
        (5, 0x580),
        (6, 0x500),
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
        (".text", 1, 6, 0x200, 1, 0, 0, 1, 0),
        (".data", 1, 3, 0x300, 64, 0, 0, 8, 0),
        (".rela.dyn", 4, 2, 0x400, len(relocations) * 24, 4, 0, 8, 24),
        (".dynsym", 11, 2, 0x500, 72, 5, 1, 8, 24),
        (".dynstr", 3, 2, 0x580, len(strings), 0, 0, 1, 0),
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


class LoadedImageSemantics(unittest.TestCase):
    def check_masks(self, image, base, expected):
        self.assertTrue(image["undefined_bytes_override_segment_bytes"])
        self.assertTrue(image["unresolved_relocations_are_open"])
        self.assertTrue(image["initialization_only"])
        self.assertEqual(len(image["objects"]), 1)
        obj = image["objects"][0]
        actual = [
            (r["address"] - base, r["size"], r["reason"])
            for r in obj["undefined_bytes"]
        ]
        self.assertEqual(sorted(actual), sorted(expected), "exact unknown extents")
        unknown = {
            r["address"] + i for r in obj["undefined_bytes"] for i in range(r["size"])
        }
        wanted = {
            base + offset + i for offset, size, _ in expected for i in range(size)
        }
        self.assertEqual(unknown, wanted, "exact byte mask")
        return obj

    def test_real_elf_unresolved_and_pending_extents(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "relocations.so"
            # PC32=4, absolute=8, IRELATIVE pending resolver=8, TLSDESC=16.
            elf_fixture(
                path, ((0, 2, 1, 0), (8, 1, 1, 0), (24, 37, 0, 0x200), (40, 36, 1, 0))
            )
            project = load_object_set(path)
            base = project.loader.main_object.mapped_base
            image = json.loads(json.dumps(loaded_image_data(project)))
            expected = [
                (0x300, 4, "unresolved-relocation"),
                (0x308, 8, "unresolved-relocation"),
                (0x318, 8, "pending-resolver"),
                (0x328, 16, "unsupported-tls-descriptor"),
            ]
            obj = self.check_masks(image, base, expected)
            self.assertEqual(
                sorted(
                    (r["address"] - base, r["resolved"]) for r in obj["relocations"]
                ),
                [(0x300, False), (0x308, False), (0x318, False)],
                "unresolved and pending records remain open",
            )
            self.assertEqual(
                obj["sha256"], hashlib.sha256(path.read_bytes()).hexdigest()
            )
            self.assertEqual(Path(obj["path"]).resolve(), path.resolve())
            self.assertEqual(obj["linked_base"], 0)
            self.assertFalse(project.is_hooked(project.entry))
            # Unknown metadata overlays bytes; it must not erase the raw snapshot.
            segment = next(
                s
                for s in obj["segments"]
                if s["address"] <= base + 0x328 < s["address"] + s["size"]
            )
            raw = bytes.fromhex(segment["bytes"])
            offset = base + 0x328 - segment["address"]
            self.assertEqual(raw[offset : offset + 16], bytes(range(0xA8, 0xB8)))
            self.assertEqual(raw[base + 0x304 - segment["address"]], 0x84)
            self.assertEqual(raw[base + 0x338 - segment["address"]], 0xB8)
            rejected_masks = 0
            for corrupt in (
                [],
                [dict(r, size=r["size"] + 1) for r in obj["undefined_bytes"]],
            ):
                damaged = json.loads(json.dumps(image))
                damaged["objects"][0]["undefined_bytes"] = corrupt
                with self.assertRaisesRegex(AssertionError, "exact unknown extents"):
                    self.check_masks(damaged, base, expected)
                rejected_masks += 1
            self.assertEqual(rejected_masks, 2, "all mask corruption controls ran")

    def test_exact_objects_and_hash_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entry, library, spec = (
                root / "entry.so",
                root / "library.so",
                root / "objects.json",
            )
            elf_fixture(entry)
            elf_fixture(library)
            record = {
                "path": str(library),
                "base_addr": 0x900000,
                "sha256": hashlib.sha256(library.read_bytes()).hexdigest(),
            }
            spec.write_text(json.dumps([record]))
            image = loaded_image_data(load_object_set(entry, spec))
            self.assertEqual(
                {Path(o["path"]).resolve() for o in image["objects"]},
                {entry.resolve(), library.resolve()},
            )
            self.assertEqual(
                next(
                    o["mapped_base"]
                    for o in image["objects"]
                    if Path(o["path"]) == library
                ),
                0x900000,
            )
            record["sha256"] = "0" * 64
            spec.write_text(json.dumps([record]))
            with self.assertRaisesRegex(ValueError, "object hash mismatch"):
                load_object_set(entry, spec)

    def test_extent_provider_boundaries(self):
        owner = SimpleNamespace(arch=SimpleNamespace(bytes=8), imports={})
        symbol = SimpleNamespace(name="copy", size=24, is_import=False)
        self.assertEqual(
            relocation_write_size(R_X86_64_PC32(owner, symbol, 0, addend=0)), 4
        )
        self.assertEqual(
            relocation_write_size(R_X86_64_64(owner, symbol, 0, addend=0)), 8
        )
        self.assertEqual(
            relocation_write_size(
                GenericTLSDescriptorReloc(owner, symbol, 0, addend=0)
            ),
            16,
        )
        copy = R_X86_64_COPY(owner, symbol, 0, addend=0)
        self.assertEqual(relocation_write_size(copy), 24)
        copy.resolvedby = SimpleNamespace(size=24)
        self.assertEqual(relocation_write_size(copy), 24)
        copy.resolvedby = SimpleNamespace(size=0)
        self.assertEqual(relocation_write_size(copy), 24)
        copy.resolvedby = SimpleNamespace(size=16)
        with self.assertRaisesRegex(ValueError, "size mismatch"):
            relocation_write_size(copy)
        copy.resolvedby = None
        rejected_sizes = 0
        for size in (None, 0, -1, True, "24"):
            symbol.size = size
            with self.assertRaisesRegex(ValueError, "positive extent"):
                relocation_write_size(copy)
            rejected_sizes += 1
        self.assertEqual(rejected_sizes, 5, "all invalid COPY extents checked")

        class UnknownRelocation(Relocation):
            def relocate(self):
                return True

        with self.assertRaisesRegex(ValueError, "unsupported relocation write extent"):
            relocation_write_size(UnknownRelocation(owner, symbol, 0))

    def test_unknown_elf_relocation_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unsupported.so"
            elf_fixture(path, ((0, 999, 1, 0),))
            with self.assertRaisesRegex(
                ValueError, "unsupported skipped ELF relocation 999"
            ):
                loaded_image_data(load_object_set(path))


if __name__ == "__main__":
    unittest.main()
