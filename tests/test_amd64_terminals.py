import hashlib
import json
import unittest
from pathlib import Path
from types import SimpleNamespace

import angr

from extractor.amd64_state import step_instruction_outcomes
from extractor.amd64_terminals import (
    is_ud2_instruction,
    is_ud2_no_decode_terminal,
)
from extractor.artifact import LocalEdge, StaticOccurrenceId
from extractor.binary_cfg import (
    _validate_block_partition,
    _walk_function,
)
from extractor.fresh import _local_edges, artifact_declarations


class Ud2TerminalTests(unittest.TestCase):
    def test_instruction_adapter_emits_one_unchanged_state_ud2_fault(self):
        address = 0x400000
        project = angr.load_shellcode(
            b"\x0f\x0b", arch="amd64", load_address=address
        )

        family = step_instruction_outcomes(project, address)

        self.assertEqual(family.source, address)
        self.assertEqual(len(family.outcomes), 1)
        outcome = family.outcomes[0]
        self.assertEqual(outcome.jumpkind, "Ijk_SigILL")
        self.assertEqual(outcome.target_value, address)
        self.assertEqual(outcome.updates, {})
        self.assertEqual(outcome.writes, ())
        edge = _local_edges(
            artifact_declarations(project.arch),
            StaticOccurrenceId(0),
            family,
        )[0]
        self.assertEqual(edge.summary.target.kind, "error")
        self.assertEqual(edge.jumpkind, "Ijk_SigILL")
        self.assertEqual(edge.fault_kind, "invalid_opcode")
        self.assertEqual(LocalEdge.from_data(edge.to_data()), edge)

    def test_minimized_synthetic_ud2_is_a_valid_terminal(self):
        code = b"\x0f\x0b"
        instruction = {
            "mnemonic": "ud2",
            "bytes": code.hex(),
            "size": len(code),
            "address": 0x1000,
        }
        self.assertTrue(is_ud2_instruction(instruction))
        self.assertTrue(
            is_ud2_no_decode_terminal(
                "Ijk_NoDecode",
                [instruction],
                block_end=0x1002,
                has_zero_length_imark=False,
            )
        )

    def test_pinned_apache_cold_symbol_fixtures_end_in_ud2(self):
        fixture_dir = Path(__file__).parent / "fixtures" / "apache-httpd-2.4.69"
        self.assertTrue((fixture_dir / "LICENSE").is_file())
        self.assertTrue((fixture_dir / "NOTICE").is_file())
        for name in ("ap_expr_yyrestart.cold", "ap_expr_yylex.cold"):
            with self.subTest(symbol=name):
                record = json.loads(
                    (fixture_dir / f"{name}.json").read_text(encoding="utf-8")
                )
                self.assertEqual(record["version"], "2.4.69")
                self.assertEqual(
                    record["binary_sha256"],
                    "7a850a2d913a2bcbc4a87b809b5362bc0a23a005e5590137abf42e997d7ca2d9",
                )
                code = (fixture_dir / record["fixture_file"]).read_bytes()
                self.assertEqual(len(code), record["size"])
                self.assertEqual(
                    hashlib.sha256(code).hexdigest(), record["fixture_sha256"]
                )
                self.assertTrue(code.endswith(b"\x0f\x0b"))
                instruction = {"mnemonic": "ud2", "bytes": code[-2:].hex(),
                               "size": 2, "address": record["address"] + len(code) - 2}
                self.assertTrue(is_ud2_instruction(instruction))
                self.assertTrue(is_ud2_no_decode_terminal(
                    "Ijk_NoDecode", [instruction],
                    block_end=record["address"] + len(code),
                    has_zero_length_imark=False,
                ))

    def test_pinned_apache_symbols_are_accepted_by_static_cfg_inventory(self):
        fixture_dir = Path(__file__).parent / "fixtures" / "apache-httpd-2.4.69"
        for name in ("ap_expr_yyrestart.cold", "ap_expr_yylex.cold"):
            with self.subTest(symbol=name):
                record = json.loads(
                    (fixture_dir / f"{name}.json").read_text(encoding="utf-8")
                )
                code = (fixture_dir / record["fixture_file"]).read_bytes()
                address = record["address"]
                pinned = SimpleNamespace(
                    project=angr.load_shellcode(
                        code, arch="amd64", load_address=address
                    ),
                    manifest={"open_transfers": True},
                )

                blocks, calls, indirect_sites = _walk_function(
                    pinned,
                    root_name=name,
                    root={"address": address, "size": len(code)},
                    jump_tables={},
                )

                terminal = blocks[-1]
                self.assertEqual(
                    terminal["instructions"][-1]["mnemonic"], "ud2"
                )
                self.assertEqual(
                    terminal["address"] + terminal["size"],
                    address + len(code),
                )
                self.assertEqual(terminal["successors"], [])
                self.assertEqual(indirect_sites, set())
                if name == "ap_expr_yyrestart.cold":
                    self.assertEqual(len(calls), 1)
                else:
                    self.assertEqual(calls, [])

    def test_static_cfg_inventory_accepts_distinct_overlapping_instruction_streams(
        self,
    ):
        self.assertIsNone(
            _validate_block_partition(
                root_name="sample",
                entry=0x1000,
                extent_end=0x1005,
                blocks=[
                    {
                        "address": 0x1000,
                        "size": 4,
                        "instructions": [{"address": 0x1000, "size": 4}],
                        "successors": [],
                    },
                    {
                        "address": 0x1002,
                        "size": 3,
                        "instructions": [{"address": 0x1002, "size": 3}],
                        "successors": [],
                    },
                ],
            )
        )

    def test_ordinary_decode_failures_and_zero_length_imarks_are_rejected(self):
        ud2 = {"mnemonic": "ud2", "bytes": "0f0b", "size": 2,
               "address": 0x1002}
        ordinary = {"mnemonic": "mov", "bytes": "4889", "size": 2,
                    "address": 0x1002}
        for instructions, zero_mark in (([ordinary], False), ([ud2], True)):
            with self.subTest(instructions=instructions, zero_mark=zero_mark):
                self.assertFalse(is_ud2_no_decode_terminal(
                    "Ijk_NoDecode", instructions,
                    block_end=0x1004, has_zero_length_imark=zero_mark,
                ))
        self.assertFalse(is_ud2_no_decode_terminal(
            "Ijk_NoDecode", [ud2], block_end=0x1003,
            has_zero_length_imark=False,
        ))
        self.assertFalse(is_ud2_no_decode_terminal(
            "Ijk_Boring", [ud2], block_end=0x1004,
            has_zero_length_imark=False,
        ))


if __name__ == "__main__":
    unittest.main()
