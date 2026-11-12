import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from extractor.binary_census import _emit_failure


class FailureStreamTests(unittest.TestCase):
    def test_flushed_records_are_independent_and_match_live_log(self):
        provenance = {
            "censusId": "urn:test:run", "binarySha256": "abc", "wruhRevision": "123",
            "pythonVersion": "3.12", "ciRunId": 42, "ciRunAttempt": 2,
        }
        candidate = {"id": "fn_1", "symbol": "a\nb", "relative_address": 1}
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "failures.jsonl"
            with path.open("w", encoding="utf-8") as stream, redirect_stderr(stderr):
                _emit_failure(stream, provenance, candidate, "failed", {
                    "stage": "cfg", "code": "ValueError", "message": "bad\ninput",
                })
                # A reader can recover a complete prefix without waiting for close.
                first = path.read_text(encoding="utf-8")
                _emit_failure(stream, provenance, candidate, "incomplete", {
                    "stage": "extraction", "code": "TimeoutError", "message": "late",
                })
                second = path.read_text(encoding="utf-8")
            self.assertTrue(second.startswith(first))
            records = [json.loads(line) for line in second.splitlines()]
            self.assertEqual(records[0]["provenance"], provenance)
            self.assertEqual(records[0]["candidate"], {
                "id": "fn_1", "symbol": "a\nb", "relativeAddress": 1,
            })
            self.assertEqual((records[0]["stage"], records[0]["exceptionType"], records[0]["message"]),
                             ("cfg", "ValueError", "bad\ninput"))
            self.assertEqual(records[1]["disposition"], "incomplete")
            self.assertEqual([json.loads(line.removeprefix("CENSUS_FAILURE "))
                              for line in stderr.getvalue().splitlines()], records)

    def test_inventory_failure_has_no_candidate(self):
        stream = io.StringIO()
        with redirect_stderr(io.StringIO()):
            _emit_failure(stream, {"censusId": "run"}, None, "failed", {
                "stage": "inventory-generation", "code": "RuntimeError", "message": "bad ELF",
            })
        event = json.loads(stream.getvalue())
        self.assertIsNone(event["candidate"])
        self.assertEqual(event["exceptionType"], "RuntimeError")


if __name__ == "__main__":
    unittest.main()
