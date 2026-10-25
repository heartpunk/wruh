"""Compiler-free regressions for discovery scope, evidence, and interruption."""

from __future__ import annotations

import hashlib
import signal
import struct
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from extractor.binary_census import _candidate_manifest, _function_candidates
from extractor.function_discovery import discover_function_candidates

BASE = 0x70000000
ENTRY = BASE + 0x1000


def _function(address, blocks, **flags):
    return SimpleNamespace(addr=address, size=0x123456,
                           blocks=[SimpleNamespace(addr=start, size=size) for start, size in blocks],
                           **flags)


def _project(functions):
    section = SimpleNamespace(vaddr=ENTRY, memsize=0x1000, filesize=0x1000,
                              is_executable=True, name=".text")
    image = SimpleNamespace(mapped_base=BASE, linked_base=0x400000, sections=[section])
    cfg = SimpleNamespace(kb=SimpleNamespace(functions={function.addr: function for function in functions}),
                          should_abort=False)
    analyses = SimpleNamespace(CFGFast=lambda **_kwargs: cfg)
    return SimpleNamespace(
        loader=SimpleNamespace(main_object=image,
                               find_object_containing=lambda addr: image if ENTRY <= addr < ENTRY + 0x1000 else None),
        analyses=analyses,
        is_hooked=lambda _address: False,
    )


def _named_candidate():
    return {"id": "fn_0000000000001000", "address": ENTRY, "relative_address": 0x1000,
            "object_virtual_address": 0x401000, "size": 7, "symbol": "visible", "aliases": ["visible"]}


def _write_hidden_function_elf(path):
    """A visible CALL/RET entry reaches an unnamed MOV-immediate/RET leaf."""
    offset = 0x1000
    base = 0x400000
    code = b"\xe8\x0b\x00\x00\x00\xc3" + b"\xcc" * 10 + b"\xb8\x2a\x00\x00\x00\xc3"
    strings = b"\0visible\0"
    names = b"\0.text\0.symtab\0.strtab\0.shstrtab\0"
    symoff = (offset + len(code) + 7) & ~7
    symbol_data = bytes(24) + struct.pack("<IBBHQQ", 1, 0x12, 0, 1, base + offset, 6)
    stroff = symoff + len(symbol_data)
    namesoff = stroff + len(strings)
    shoff = (namesoff + len(names) + 7) & ~7
    data = bytearray(shoff + 5 * 64)
    ident = b"\x7fELF\x02\x01\x01" + bytes(9)
    data[:64] = struct.pack("<16sHHIQQQIHHHHHH", ident, 2, 62, 1, base + offset,
                           64, shoff, 0, 64, 56, 1, 64, 5, 4)
    data[64:120] = struct.pack("<IIQQQQQQ", 1, 5, 0, base, base,
                              offset + len(code), offset + len(code), 0x1000)
    data[offset:offset + len(code)] = code
    data[symoff:symoff + len(symbol_data)] = symbol_data
    data[stroff:stroff + len(strings)] = strings
    data[namesoff:namesoff + len(names)] = names
    sections = [
        (1, 1, 6, base + offset, offset, len(code), 0, 0, 16, 0),
        (7, 2, 0, 0, symoff, len(symbol_data), 3, 1, 8, 24),
        (15, 3, 0, 0, stroff, len(strings), 0, 0, 1, 0),
        (23, 3, 0, 0, namesoff, len(names), 0, 0, 1, 0),
    ]
    for index, section in enumerate(sections, 1):
        struct.pack_into("<IIQQQQIIQQ", data, shoff + index * 64, *section)
    path.write_bytes(data)


class DiscoveryEvidenceTests(unittest.TestCase):
    def test_block_envelope_does_not_use_cfgfast_function_size(self):
        project = _project([_function(ENTRY, [(ENTRY, 3), (ENTRY + 0x10, 2)])])
        candidates, report = discover_function_candidates(project, [])
        self.assertEqual(report["status"], "complete")
        self.assertEqual(candidates[0]["size"], 0x12)
        self.assertEqual(candidates[0]["block_ranges"], [[0x1000, 3], [0x1010, 2]])
        self.assertEqual(candidates[0]["recovered_block_bytes"], 5)
        self.assertTrue(candidates[0]["envelope_has_gaps"])
        self.assertEqual(candidates[0]["identity_basis"], "cfgfast")
        self.assertEqual(candidates[0]["aliases"], [])
        self.assertEqual(candidates[0]["object_virtual_address"], 0x401000)

    def test_named_sized_candidate_survives_smaller_recovered_scope(self):
        original = _named_candidate()
        project = _project([_function(ENTRY, [(ENTRY, 2)])])
        candidates, report = discover_function_candidates(project, [original])
        self.assertEqual(candidates, [original])
        self.assertEqual(report["new_candidate_count"], 0)
        self.assertEqual(report["recovered_candidates"][0]["recovered_extent_bytes"], 2)

    def test_excludes_external_plt_simprocedure_and_invalid_block_evidence(self):
        functions = [
            _function(ENTRY, [(ENTRY, 1)], is_plt=True),
            _function(ENTRY + 0x10, [(ENTRY + 0x10, 1)], is_simprocedure=True),
            _function(ENTRY + 0x20, []),
            _function(ENTRY + 0x30, [(ENTRY + 0x30, 1), (ENTRY + 0x2000, 1)]),
            _function(ENTRY + 0x40, [(ENTRY + 0x41, 1)]),
            _function(ENTRY + 0x2000, [(ENTRY + 0x2000, 1)]),
        ]
        candidates, report = discover_function_candidates(_project(functions), [])
        self.assertEqual(candidates, [])
        self.assertEqual(sum(report["rejected"].values()), len(functions))

    def test_partial_cfg_remains_incomplete(self):
        project = _project([_function(ENTRY, [(ENTRY, 1)])])
        cfg = project.analyses.CFGFast()
        cfg.should_abort = True
        candidates, report = discover_function_candidates(project, [])
        self.assertEqual(len(candidates), 1)
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["reason"], "analysis-aborted")

    def test_existing_timer_is_preserved_and_discovery_does_not_start(self):
        project = _project([])
        with patch.object(signal, "getitimer", return_value=(30.0, 0.0)), \
                patch.object(project.analyses, "CFGFast") as analysis:
            candidates, report = discover_function_candidates(project, [_named_candidate()])
        analysis.assert_not_called()
        self.assertEqual(candidates, [_named_candidate()])
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["reason"], "timeout-guard-unavailable")
        self.assertIn("active caller SIGALRM", report["diagnostic"])

    def test_wall_deadline_interrupts_postprocessing_and_restores_handler(self):
        project = _project([])
        cfg = project.analyses.CFGFast()

        class SlowFunction:
            addr = ENTRY

            @property
            def blocks(self):
                time.sleep(5)
                return [SimpleNamespace(addr=ENTRY, size=1)]

        cfg.kb.functions = {ENTRY: SlowFunction()}
        previous = signal.getsignal(signal.SIGALRM)

        def sentinel(_signum, _frame):
            raise AssertionError("the previous handler must not run during discovery")

        signal.signal(signal.SIGALRM, sentinel)
        try:
            candidates, report = discover_function_candidates(project, [_named_candidate()], timeout_seconds=0.02)
            self.assertIs(signal.getsignal(signal.SIGALRM), sentinel)
            self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0))
        finally:
            signal.signal(signal.SIGALRM, previous)
        self.assertEqual(candidates, [_named_candidate()])
        self.assertEqual(report["status"], "incomplete")
        self.assertTrue(report["timed_out"])
        self.assertLess(report["elapsed_seconds"], 1.0)
        self.assertEqual(report["new_candidate_count"], 0)


class ActualCfgFastDiscoveryTests(unittest.TestCase):
    def test_symbol_baseline_omits_unnamed_direct_callee_then_recovers_and_extracts(self):
        # Deliberately require the pinned runtime: missing angr must fail this test.
        from extractor import runtime
        from extractor.binary_cfg import build_static_cfg
        from extractor.binary_inventory import PinnedBinary
        from extractor.fresh import extract_fresh_function

        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "hidden-leaf.elf"
            _write_hidden_function_elf(binary)
            project = runtime.angr.Project(str(binary), auto_load_libs=False)
            symbols = _function_candidates(project)
            self.assertEqual([candidate["symbol"] for candidate in symbols], ["visible"])
            hidden = 0x401010
            self.assertNotIn(hidden, [candidate["address"] for candidate in symbols])
            candidates, report = discover_function_candidates(project, symbols, timeout_seconds=10)
            self.assertEqual(report["status"], "complete")
            candidate = next(candidate for candidate in candidates if candidate["address"] == hidden)
            self.assertEqual(candidate["block_ranges"], [[0x1010, 6]])
            self.assertEqual(candidate["symbol"], "fn_0000000000001010")
            self.assertEqual(candidate["identity_basis"], "cfgfast")
            digest = hashlib.sha256(binary.read_bytes()).hexdigest()
            manifest = _candidate_manifest(project, digest, binary, digest, candidate)
            pinned = PinnedBinary(binary, manifest, project)
            cfg = build_static_cfg(pinned)
            fresh = extract_fresh_function(pinned, cfg, candidate["id"])
            self.assertEqual([edge.source for edge in fresh.local_edges], [hidden, hidden + 5])
            self.assertEqual([occ.origin.instruction_bytes for occ in fresh.occurrences], ["b82a000000", "c3"])


if __name__ == "__main__":
    unittest.main()
