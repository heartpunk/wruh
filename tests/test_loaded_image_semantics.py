"""Small real ELF images and explicit CLE extent boundary fixtures.

The ELF writer encodes the public ELF64 format, not a mocked loader. Fixtures
are data only: no native execution and no runtime resolver results are guessed.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from extractor.native_runtime import preload_libstdcxx

preload_libstdcxx()
from extractor.backend import Session
from extractor.elf_fixture import elf_fixture


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

    def test_function_symbol_annotations_group_only_equal_extents(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "symbols.so"
            elf_fixture(path, extra_functions=[("alias_b", 0x200, 1), ("alias_a", 0x200, 1),
                                               ("overlap", 0x200, 4), ("zero", 0x202, 0)])
            obj = Session.load(path).image.loaded_image["objects"][0]
            self.assertEqual(obj["function_symbols"], [
                {"offset": 0x200, "size": 1, "names": ["alias_a", "alias_b", "fixture"]},
                {"offset": 0x200, "size": 4, "names": ["overlap"]},
                {"offset": 0x202, "size": 0, "names": ["zero"]},
            ])

    @unittest.skipUnless(os.environ.get("WRUH_LEAN_EXE"), "requires built Lean extractor")
    def test_main_entrypoints_publish_same_symbols_and_transitions(self):
        from ayxg.codec import loads
        from extractor.fresh import extract_linear, linear_site_records
        from extractor.instruction_inventory import Interval

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root / "fixture.so"
            elf_fixture(binary)
            session = Session.load(binary)
            obj = session.image.loaded_image["objects"][0]
            base = obj["mapped_base"]
            exclusions = [Interval(base, base + 0x200), Interval(base + 0x201, base + 0x1000)]
            decoded = session.inventory(exclusions)
            records = linear_site_records(decoded, chunk_size=1, seed=17)
            model = extract_linear(session, records)
            self.assertTrue(obj["function_symbols"])
            with patch.dict(obj, {"function_symbols": []}):
                decoded_without = session.inventory(exclusions)
                records_without = linear_site_records(decoded_without, chunk_size=1, seed=17)
                model_without = extract_linear(session, records_without)
            self.assertEqual([item.site_key for item in decoded.decoded],
                             [item.site_key for item in decoded_without.decoded])
            self.assertEqual(model.canonical_json(), model_without.canonical_json())

            intervals = root / "data.json"
            intervals.write_text(json.dumps([{"start": item.start, "end": item.end} for item in exclusions]))
            python_output, lean_output = root / "python.json", root / "lean.json"
            common = ["--artifact", str(binary), "--data-intervals", str(intervals),
                      "--chunk-size", "1", "--seed", "17"]
            env = dict(os.environ, WRUH_PYTHON=sys.executable)
            for command, output in (([sys.executable, "-m", "extractor.extract_cli"], python_output),
                                    ([env["WRUH_LEAN_EXE"]], lean_output)):
                subprocess.run([*command, *common, "--output", str(output)], env=env, check=True)
            python_bundle = loads(python_output.read_text())
            lean_bundle = loads(lean_output.read_text())
            self.assertEqual(python_bundle["loaded_image"]["objects"][0]["function_symbols"],
                             [{"offset": 0x200, "size": 1, "names": ["fixture"]}])
            self.assertEqual(python_bundle["loaded_image"], lean_bundle["loaded_image"])
            report = root / "parity.json"
            subprocess.run([sys.executable, "-m", "extractor.angr_upgrade_parity",
                            "--baseline", str(python_output), "--candidate", str(lean_output),
                            "--output", str(report)], env=env, check=True)
            self.assertTrue(json.loads(report.read_text())["shared_edge_parity"])

    def test_real_elf_unresolved_and_pending_extents(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "relocations.so"
            # PC32=4, absolute=8, IRELATIVE pending resolver=8, TLSDESC=16.
            elf_fixture(
                path, ((0, 2, 1, 0), (8, 1, 1, 0), (24, 37, 0, 0x200), (40, 36, 1, 0))
            )
            self.assertEqual(
                [
                    struct.unpack_from("<qQ", path.read_bytes(), 0x600 + index * 16)
                    for index in range(9)
                ],
                [
                    (5, 0x580),
                    (6, 0x500),
                    (7, 0x400),
                    (8, 96),
                    (9, 24),
                    (10, 18),
                    (11, 24),
                    (0, 0),
                    (0, 0),
                ],
                "fixture dynamic inventory must be present even when CLE can use sections",
            )
            image = Session.load(path).image.loaded_image
            base = image["objects"][0]["mapped_base"]
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
            self.assertIn({"offset": 0x200, "size": 1, "names": ["fixture"]},
                          obj["function_symbols"])
            self.assertEqual(obj["linked_base"], 0)
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
            image = Session.load(entry, spec).image.loaded_image
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
                Session.load(entry, spec)

    def test_copy_extent_uses_symbol_size(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "copy.so"
            elf_fixture(path, [(0, 5, 1, 0)], import_size=24)
            image = Session.load(path).image.loaded_image
            base = image["objects"][0]["mapped_base"]
            self.check_masks(image, base, [(0x300, 24, "unresolved-relocation")])

    def test_unknown_elf_relocation_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unsupported.so"
            elf_fixture(path, ((0, 999, 1, 0),))
            with self.assertRaisesRegex(
                ValueError, "unsupported skipped ELF relocation 999"
            ):
                Session.load(path)


if __name__ == "__main__":
    unittest.main()
