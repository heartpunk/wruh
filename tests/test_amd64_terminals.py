import hashlib
import json
import unittest
from pathlib import Path

import tempfile

from ayxg.expr import TypedExpr

from extractor.elf_fixture import PC, code_inventory, code_session
from extractor.instruction_inventory import Interval
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

    def test_complete_ud2_decodes_as_one_instruction(self):
        code = b"\x0f\x0b"
        session = code_session(self.enterContext(tempfile.TemporaryDirectory()), code)
        decoded = code_inventory(session, len(code))
        instruction, = decoded.decoded
        self.assertEqual((instruction.address, instruction.data, instruction.mnemonic), (PC, code, "ud2"))
        self.assertFalse(decoded.unresolved or decoded.unexamined)

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
                session = code_session(self.enterContext(tempfile.TemporaryDirectory()), code)
                terminal = code_inventory(session, len(code)).decoded[-1]
                self.assertEqual((terminal.mnemonic, terminal.address), ("ud2", PC + len(code) - 2))
                outcome, = session.step(terminal.address).outcomes
                self.assertEqual((outcome.fault_kind, outcome.target_value), ("invalid_opcode", terminal.address))

    def test_incomplete_instruction_is_unresolved(self):
        for code in (b"\x0f", b"\x48\x89"):
            with self.subTest(code=code):
                session = code_session(self.enterContext(tempfile.TemporaryDirectory()), code)
                result = code_inventory(session, len(code))
                self.assertEqual(result.decoded, ())
                self.assertEqual(result.unresolved, (Interval(PC, PC + 1),))


if __name__ == "__main__":
    unittest.main()
