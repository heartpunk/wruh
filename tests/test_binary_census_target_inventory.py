"""A compiler-free, MIT-licensed Bun carve exercises real function recovery.

The original leaf is loaded only as data. A symbols-only baseline must omit it
for the intended inventory reason before recovery and fresh extraction succeed.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import struct
import tempfile
import unittest
from pathlib import Path

from extractor.binary_census import _candidate_manifest, _function_candidates

FIXTURE = Path(__file__).parent / "fixtures" / "bun-inventory"
BASE = 0x400000
TEXT_OFFSET = 0x1000
CARVE_OFFSET = 0x40
CARVE_ADDRESS = BASE + TEXT_OFFSET + CARVE_OFFSET
CARVE_SHA256 = "a942da11845b6a008ce32f9ce732481b443232c6925051fc03ea98e6a37acb83"
INSTRUCTION_OFFSETS = (0, 1, 4, 7, 9, 12, 14, 20, 22, 24, 29, 32, 33, 34, 39, 40)


def write_carved_fixture(path: Path, code: bytes) -> None:
    """Reuse the existing open-transfers fixture's ELF64 encoding convention.

    Only the six-byte synthetic entry has a symbol. Its direct call reaches the
    unchanged Bun excerpt after INT3 padding; no compiler or linker is needed.
    """
    entry = b"\xe8" + struct.pack("<i", CARVE_OFFSET - 5) + b"\xc3"
    text = entry + b"\xcc" * (CARVE_OFFSET - len(entry)) + code
    strings = b"\0fixture_entry\0"
    symbols = bytes(24) + struct.pack(
        "<IBBHQQ", 1, 0x12, 0, 1, BASE + TEXT_OFFSET, len(entry)
    )
    section_names = b"\0.text\0.symtab\0.strtab\0.shstrtab\0"
    sym_offset = (TEXT_OFFSET + len(text) + 7) & ~7
    str_offset = sym_offset + len(symbols)
    names_offset = str_offset + len(strings)
    sections_offset = (names_offset + len(section_names) + 7) & ~7
    raw = bytearray(sections_offset + 5 * 64)
    ident = b"\x7fELF\x02\x01\x01" + bytes(9)
    raw[:64] = struct.pack(
        "<16sHHIQQQIHHHHHH", ident, 2, 62, 1, BASE + TEXT_OFFSET,
        64, sections_offset, 0, 64, 56, 1, 64, 5, 4,
    )
    raw[64:120] = struct.pack(
        "<IIQQQQQQ", 1, 5, 0, BASE, BASE,
        TEXT_OFFSET + len(text), TEXT_OFFSET + len(text), 0x1000,
    )
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
        offset = sections_offset + index * 64
        raw[offset:offset + 64] = struct.pack("<IIQQQQIIQQ", *section)
    path.write_bytes(raw)


def require_carved_candidate(candidates):
    matches = [item for item in candidates if item["address"] == CARVE_ADDRESS]
    if len(matches) != 1:
        raise AssertionError("carved Bun function missing from candidate inventory")
    return matches[0]


class BunFixtureProvenanceTests(unittest.TestCase):
    def test_carve_retains_exact_bytes_and_upstream_attribution(self):
        code = (FIXTURE / "napi_get_version.bin").read_bytes()
        metadata = json.loads((FIXTURE / "provenance.json").read_text())
        self.assertEqual(len(code), 41)
        self.assertEqual(hashlib.sha256(code).hexdigest(), CARVE_SHA256)
        self.assertEqual(metadata["carve"]["sha256"], CARVE_SHA256)
        self.assertEqual(metadata["carve"]["bytesHex"], code.hex())
        self.assertEqual(metadata["carve"]["instructionOffsets"], list(INSTRUCTION_OFFSETS))
        self.assertFalse(metadata["carve"]["rewrittenBytes"])
        self.assertEqual(metadata["carve"]["externalCalls"], [])
        self.assertEqual(metadata["carve"]["instructionPointerRelativeMemoryReferences"], [])
        self.assertEqual(metadata["source"]["revision"], "744846f844374847c902b5e7fd59b4342a51ef99")
        self.assertNotEqual(metadata["origin"]["binarySha256"], metadata["relatedCensus"]["binarySha256"])
        self.assertEqual(metadata["relatedCensus"]["disposition"], "extracted")
        self.assertEqual(metadata["license"], "MIT")
        self.assertIn("Bun itself is MIT-licensed.", (FIXTURE / "LICENSE.upstream.md").read_text())
        self.assertIn("Permission is hereby granted, free of charge", (FIXTURE / "MIT.txt").read_text())
        self.assertEqual(
            hashlib.sha256((FIXTURE / "LICENSE.upstream.md").read_bytes()).hexdigest(),
            metadata["upstreamLicense"]["sha256"],
        )
        self.assertEqual(
            hashlib.sha256((FIXTURE / "napi_get_version.rs").read_bytes()).hexdigest(),
            metadata["source"]["excerptSha256"],
        )


class BunTargetInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        missing = [name for name in ("angr", "ayxg") if importlib.util.find_spec(name) is None]
        if missing:
            message = "pinned extraction runtime unavailable: " + ", ".join(missing)
            if os.environ.get("GITHUB_ACTIONS") == "true":
                raise RuntimeError(message)
            raise unittest.SkipTest(message)
        from extractor.native_runtime import preload_libstdcxx

        preload_libstdcxx()

    def test_unnamed_bun_body_is_recovered_and_freshly_extracted(self):
        import angr

        from extractor.binary_cfg import build_static_cfg
        from extractor.binary_inventory import PinnedBinary
        from extractor.fresh import FreshFunction, extract_fresh_function

        code = (FIXTURE / "napi_get_version.bin").read_bytes()
        self.assertEqual(hashlib.sha256(code).hexdigest(), CARVE_SHA256)
        with tempfile.TemporaryDirectory() as temporary_directory:
            binary = Path(temporary_directory) / "bun-napi-get-version.elf"
            write_carved_fixture(binary, code)
            project = angr.Project(str(binary), auto_load_libs=False)
            self.assertEqual(project.arch.name, "AMD64")
            self.assertEqual(project.loader.memory.load(CARVE_ADDRESS, len(code)), code)

            # This is the baseline rejection control: loading and symbol
            # inventory work, but the intended function has no sized symbol.
            baseline = _function_candidates(project)
            self.assertEqual([item["symbol"] for item in baseline], ["fixture_entry"])
            with self.assertRaisesRegex(AssertionError, "carved Bun function missing"):
                require_carved_candidate(baseline)

            # Keeping this test runnable against the old source makes the
            # baseline fail for the intended missing function, rather than
            # for the absence of the new discovery module.
            try:
                from extractor.function_discovery import discover_function_candidates
            except ModuleNotFoundError as error:
                if error.name != "extractor.function_discovery":
                    raise
                candidates = baseline
                recovery = {"status": "complete"}
            else:
                candidates, recovery = discover_function_candidates(
                    project, baseline, timeout_seconds=30.0
                )
            candidate = require_carved_candidate(candidates)
            self.assertEqual(recovery["status"], "complete")
            self.assertEqual(candidate["identity_basis"], "cfgfast")
            self.assertEqual(candidate["aliases"], [])
            self.assertEqual(candidate["size"], len(code))
            self.assertEqual(candidate["recovered_block_bytes"], len(code))
            self.assertFalse(candidate["envelope_has_gaps"])

            digest = hashlib.sha256(binary.read_bytes()).hexdigest()
            manifest = _candidate_manifest(project, digest, binary, digest, candidate)
            pinned = PinnedBinary(binary, manifest, project)
            cfg = build_static_cfg(pinned)
            fresh = extract_fresh_function(pinned, cfg, candidate["id"])
            self.assertEqual(fresh.entry, CARVE_ADDRESS)
            self.assertEqual(
                {item.origin.canonical_address for item in fresh.occurrences},
                {CARVE_ADDRESS + offset for offset in INSTRUCTION_OFFSETS},
            )
            for occurrence in fresh.occurrences:
                origin = occurrence.origin
                offset = origin.canonical_address - CARVE_ADDRESS
                instruction_bytes = bytes.fromhex(origin.instruction_bytes)
                self.assertEqual(instruction_bytes, code[offset:offset + len(instruction_bytes)])
                self.assertEqual(origin.image_sha256, digest)
            model = fresh.canonical_json()
            restored = FreshFunction.from_data(json.loads(model))
            self.assertEqual(restored.canonical_json(), model)
            self.assertEqual(restored.entry, CARVE_ADDRESS)
            self.assertTrue(restored.local_edges)


if __name__ == "__main__":
    unittest.main()
