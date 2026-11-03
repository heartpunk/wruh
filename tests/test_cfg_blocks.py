import hashlib
import json
from pathlib import Path
import unittest

from extractor.cfg_blocks import (
    CfgBlockValidationError,
    instruction_index,
    ordered_instruction_records,
    successor_index,
    validate_block_partition,
)


def _overlapping_blocks():
    shared_instruction = {
        "address": 0x1001,
        "bytes": "eb00",
        "mnemonic": "jmp",
        "op_str": "0x1003",
        "size": 2,
    }
    return [
        {
            "address": 0x1000,
            "size": 3,
            "instructions": [
                {
                    "address": 0x1000,
                    "bytes": "90",
                    "mnemonic": "nop",
                    "op_str": "",
                    "size": 1,
                },
                shared_instruction,
            ],
            "successors": [0x1001],
        },
        {
            "address": 0x1001,
            "size": 2,
            "instructions": [dict(shared_instruction)],
            "successors": [0x1000],
        },
    ]


class CfgBlockOverlapTests(unittest.TestCase):
    def test_overlapping_instruction_streams_are_validated_and_indexed(self):
        blocks = _overlapping_blocks()

        validate_block_partition(
            root_name="fixture",
            entry=0x1000,
            extent_end=0x1003,
            blocks=blocks,
        )

        indexed = instruction_index(blocks)
        self.assertEqual(tuple(indexed), (0x1000, 0x1001))
        self.assertEqual(
            [item["address"] for item in ordered_instruction_records(blocks)],
            [0x1000, 0x1001],
        )
        self.assertEqual(
            successor_index(blocks),
            {0x1000: (0x1001,), 0x1001: (0x1000, 0x1001)},
        )

    def test_conflicting_decode_at_shared_instruction_address_is_rejected(self):
        blocks = _overlapping_blocks()
        blocks[1]["instructions"][0]["bytes"] = "9090"

        with self.assertRaisesRegex(
            CfgBlockValidationError, "conflicting instruction decode at 0x1001"
        ):
            validate_block_partition(
                root_name="fixture",
                entry=0x1000,
                extent_end=0x1003,
                blocks=blocks,
            )

    def test_block_outside_function_extent_is_rejected(self):
        with self.assertRaisesRegex(CfgBlockValidationError, "leaves"):
            validate_block_partition(
                root_name="fixture",
                entry=0x1000,
                extent_end=0x1002,
                blocks=_overlapping_blocks(),
            )

    def test_successor_not_in_local_block_inventory_is_rejected(self):
        blocks = _overlapping_blocks()
        blocks[1]["successors"] = [0x2000]

        with self.assertRaisesRegex(
            CfgBlockValidationError, "local successors are not block entries"
        ):
            validate_block_partition(
                root_name="fixture",
                entry=0x1000,
                extent_end=0x1003,
                blocks=blocks,
            )


class ApacheCompiledFixtureTests(unittest.TestCase):
    def test_release_files_and_real_overlapping_function_fixtures(self):
        fixture_dir = (
            Path(__file__).parent / "fixtures" / "apache-httpd-2.4.69"
        )
        self.assertTrue((fixture_dir / "LICENSE").is_file())
        self.assertTrue((fixture_dir / "NOTICE").is_file())
        expected_sources = {
            "ap_fini_vhost_config": "server/vhost.c",
            "ap_pass_brigade_fchk": "server/util_filter.c",
        }

        for symbol, source_path in expected_sources.items():
            with self.subTest(symbol=symbol):
                record = json.loads(
                    (fixture_dir / f"{symbol}.json").read_text(
                        encoding="utf-8"
                    )
                )
                machine_code = (fixture_dir / f"{symbol}.bin").read_bytes()
                self.assertEqual(record["version"], "2.4.69")
                self.assertEqual(record["symbol"], symbol)
                self.assertEqual(record["source_path"], source_path)
                self.assertEqual(
                    record["binary_sha256"],
                    "7a850a2d913a2bcbc4a87b809b5362bc0a23a005e5590137abf42e997d7ca2d9",
                )
                self.assertEqual(len(machine_code), record["size"])
                self.assertEqual(
                    hashlib.sha256(machine_code).hexdigest(),
                    record["code_sha256"],
                )
                validate_block_partition(
                    root_name=symbol,
                    entry=record["entry_address"],
                    extent_end=record["entry_address"] + record["size"],
                    blocks=record["blocks"],
                )

                overlap_count = 0
                blocks = record["blocks"]
                for index, left in enumerate(blocks):
                    for right in blocks[index + 1:]:
                        overlap_count += int(
                            max(left["address"], right["address"])
                            < min(
                                left["address"] + left["size"],
                                right["address"] + right["size"],
                            )
                        )
                    for instruction in left["instructions"]:
                        offset = instruction["address"] - record["entry_address"]
                        length = instruction["size"]
                        self.assertEqual(
                            bytes.fromhex(instruction["bytes"]),
                            machine_code[offset:offset + length],
                        )
                self.assertGreater(overlap_count, 0)


if __name__ == "__main__":
    unittest.main()
