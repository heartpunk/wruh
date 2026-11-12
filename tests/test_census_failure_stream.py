import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from extractor import binary_census
from extractor.binary_census import _emit_failure
from tools.capture_census_failures import capture


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

    def test_candidate_failure_is_streamed_before_the_next_candidate_and_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root / "binary"
            binary.write_bytes(b"fixture")
            output = root / "out"
            candidates = [
                {"id": f"fn_{index}", "symbol": f"symbol_{index}",
                 "relative_address": index, "object_virtual_address": index,
                 "address": index, "size": 4, "aliases": [f"symbol_{index}"]}
                for index in (1, 2)
            ]
            image = SimpleNamespace(binary=str(binary), pic=False)
            project = SimpleNamespace(arch=SimpleNamespace(name="AMD64", bits=64),
                                      loader=SimpleNamespace(main_object=image))
            modules = {}
            def module(name, **values):
                result = ModuleType(name)
                result.__dict__.update(values)
                modules[name] = result
            def fail_cfg(_pinned):
                raise ValueError("failure from cfg")
            def manifest(_project, _digest, _path, _object_digest, candidate):
                if candidate["id"] == "fn_2":
                    prior = json.loads((output / "failures.jsonl").read_text())
                    self.assertEqual(prior["candidate"]["id"], "fn_1")
                    self.assertEqual(prior["message"], "failure from cfg")
                    raise KeyboardInterrupt
                return {}
            module("angr", Project=lambda *_a, **_kw: project)
            module("extractor.native_runtime", preload_libstdcxx=lambda: None)
            module("extractor.amd64_state", clear_smt_translation_cache=lambda: None)
            module("extractor.binary_cfg", build_static_cfg=fail_cfg)
            module("extractor.binary_inventory", PinnedBinary=lambda *_a: object())
            module("extractor.fresh", extract_fresh_function=lambda *_a: None)
            argv = ["binary_census", "--binary", str(binary), "--target-id", "fixture",
                    "--target-version", "1", "--output-dir", str(output),
                    "--wruh-revision", "source-rev", "--ayxg-revision", "ayxg-rev"]
            with (patch.dict(sys.modules, modules), patch.object(sys, "argv", argv),
                  patch.object(binary_census, "_function_candidates", return_value=candidates),
                  patch.object(binary_census, "_candidate_manifest", side_effect=manifest),
                  patch.object(binary_census, "_is_github_actions_runner", return_value=False),
                  redirect_stderr(io.StringIO()), patch("sys.stdout", new=io.StringIO())):
                self.assertEqual(binary_census.main(), 130)
            records = [json.loads(line) for line in (output / "failures.jsonl").read_text().splitlines()]
            self.assertEqual([(e["stage"], e["exceptionType"]) for e in records],
                             [("cfg", "ValueError"), ("inventory", "KeyboardInterrupt")])
            self.assertEqual(records[0]["provenance"]["wruhRevision"], "source-rev")
            self.assertEqual(records[0]["provenance"]["ayxgRevision"], "ayxg-rev")
            self.assertEqual(records[0]["provenance"]["binarySha256"],
                             binary_census._sha256(binary))
            ledger = [json.loads(line) for line in (output / "entries.jsonl").read_text().splitlines()]
            self.assertEqual([e["disposition"] for e in ledger], ["failed", "incomplete"])
            graph = json.loads((output / "census.jsonld").read_text())["@graph"]
            self.assertTrue(any(n.get("bfe:diagnosticText") == "failure from cfg" for n in graph))
            self.assertTrue(json.loads((output / "summary.json").read_text())["interrupted"])

    def test_capture_forwards_output_and_preserves_complete_failure_prefix(self):
        source = io.StringIO('progress\nCENSUS_FAILURE {"candidate":"fn_1"}\n'
                             'CENSUS_FAILURE {"unfinished":')
        retained, forwarded = io.StringIO(), io.StringIO()
        capture(source, retained, forwarded)
        self.assertEqual(retained.getvalue(), '{"candidate":"fn_1"}\n')
        self.assertIn('progress\n', forwarded.getvalue())
        self.assertIn('{"unfinished":', forwarded.getvalue())

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
