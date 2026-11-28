import hashlib
import json
import unittest
from pathlib import Path

import tempfile

from ayxg.expr import TypedExpr

from extractor.elf_fixture import PC, code_session
from extractor.amd64_terminals import (
    is_ud2_instruction,
    is_ud2_no_decode_terminal,
)
from extractor.artifact import LocalEdge, StaticOccurrenceId
from extractor.fresh import _local_edges


class Ud2TerminalTests(unittest.TestCase):
    def test_instruction_adapter_emits_one_unchanged_state_ud2_fault(self):
        address = PC
        session = code_session(self.enterContext(tempfile.TemporaryDirectory()), b"\x0f\x0b")
        family = session.step(address)
        self.assertEqual(family.address, address)
        self.assertEqual(len(family.outcomes), 1)
        outcome = family.outcomes[0]
        self.assertEqual(outcome.jumpkind, "Ijk_SigILL")
        self.assertEqual(outcome.target_value, address)
        self.assertEqual(dict(outcome.updates), {d.name: TypedExpr.var(d.name, d.sort)
                                                 for d in session.image.declarations})
        self.assertEqual(outcome.writes, ())
        edge = _local_edges(
            session.image.declarations,
            StaticOccurrenceId(0),
            family,
        )[0]
        self.assertEqual(edge.summary.target.kind, "error")
        self.assertEqual(edge.jumpkind, "Ijk_SigILL")
        self.assertEqual(edge.fault_kind, "invalid_opcode")
        restored = LocalEdge.from_data(edge.to_data())
        self.assertEqual(restored.jumpkind, "Ijk_SigILL")
        self.assertEqual(restored.fault_kind, "invalid_opcode")

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
