import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from extractor.binary_census import (
    _candidate_manifest,
    _entry_nodes,
    _function_candidates,
    _select_candidates,
)


class FunctionCandidateAddressTests(unittest.TestCase):
    def _project(
        self,
        *,
        linked_base: int,
        mapped_base: int,
        linked_address: int,
        rebased_address: int,
        pic: bool,
    ) -> SimpleNamespace:
        symbol = SimpleNamespace(
            name="sample_function",
            size=0x20,
            type=SimpleNamespace(name="TYPE_FUNCTION"),
            is_import=False,
            relative_addr=0x1000,
            linked_addr=linked_address,
            rebased_addr=rebased_address,
        )
        image = SimpleNamespace(
            symbols=[symbol],
            linked_base=linked_base,
            mapped_base=mapped_base,
            pic=pic,
            binary="/tmp/fixture",
        )
        return SimpleNamespace(
            loader=SimpleNamespace(main_object=image),
            arch=SimpleNamespace(name="AMD64", bits=64),
        )

    def _assert_candidate(self, project, expected_object_va, expected_rebased):
        candidate = _function_candidates(project)[0]
        self.assertEqual(candidate["id"], "fn_0000000000001000")
        self.assertEqual(candidate["relative_address"], 0x1000)
        self.assertEqual(candidate["object_virtual_address"], expected_object_va)
        self.assertEqual(candidate["address"], expected_rebased)

        manifest = _candidate_manifest(
            project,
            binary_digest="binary-digest",
            object_path=Path("/tmp/fixture"),
            object_digest="object-digest",
            candidate=candidate,
        )
        root = manifest["roots"][candidate["id"]]
        self.assertEqual(root["address"], expected_rebased)
        self.assertIn(candidate["id"], manifest["call_graph"])

        nodes, _ = _entry_nodes(
            census_id="urn:test:census",
            candidate=candidate,
            binary_id="urn:test:binary",
            disposition="failed",
            attempt_id="urn:test:attempt",
            started="2026-01-01T00:00:00Z",
            ended="2026-01-01T00:00:01Z",
            tool_release_ids=[],
        )
        candidate_node = next(node for node in nodes if node["@type"] == "bfe:FunctionCandidate")
        self.assertEqual(
            candidate_node["bfe:candidateAddressSpace"]["@id"],
            "bfe:ObjectVirtualAddress",
        )
        self.assertEqual(candidate_node["bfe:candidateAddressValue"], expected_object_va)

    def test_nonzero_linked_base_executable_reports_linked_object_va(self):
        # ET_EXEC linked at 0x400000; CLE's relative symbol offset is 0x1000.
        project = self._project(
            linked_base=0x400000,
            mapped_base=0x400000,
            linked_address=0x401000,
            rebased_address=0x401000,
            pic=False,
        )
        self._assert_candidate(project, expected_object_va=0x401000, expected_rebased=0x401000)

    def test_zero_linked_base_pie_reports_object_va_not_runtime_rebase(self):
        # ET_DYN/PIE has linked base 0; the loader maps it at a nonzero address.
        project = self._project(
            linked_base=0,
            mapped_base=0x70000000,
            linked_address=0x1000,
            rebased_address=0x70001000,
            pic=True,
        )
        self._assert_candidate(project, expected_object_va=0x1000, expected_rebased=0x70001000)


class ExplicitFunctionSelectionTests(unittest.TestCase):
    def setUp(self):
        self.candidates = [
            {"id": "fn_1", "symbol": "first", "aliases": ["first", "first_alias"]},
            {"id": "fn_2", "symbol": "second", "aliases": ["second"]},
            {"id": "fn_3", "symbol": "third", "aliases": ["third"]},
        ]

    def test_only_named_candidates_are_selected(self):
        selected, metadata = _select_candidates(
            self.candidates,
            "00" * 32,
            None,
            None,
            ["first_alias", "second"],
        )
        self.assertEqual(selected, {"fn_1", "fn_2"})
        self.assertEqual(metadata["selectedCount"], 2)
        self.assertEqual(metadata["samplingPolicy"], "explicit-symbols-v1")
        self.assertEqual(metadata["selectedSymbols"], ["first_alias", "second"])

    def test_unknown_and_ambiguous_symbols_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown symbols"):
            _select_candidates(self.candidates, "00" * 32, None, None, ["missing"])

        ambiguous = [
            *self.candidates,
            {"id": "fn_4", "symbol": "other", "aliases": ["other", "second"]},
        ]
        with self.assertRaisesRegex(ValueError, "ambiguous symbols"):
            _select_candidates(ambiguous, "00" * 32, None, None, ["second"])

    def test_only_symbols_cannot_be_combined_with_sampling(self):
        with self.assertRaisesRegex(ValueError, "cannot be combined with sampling"):
            _select_candidates(
                self.candidates,
                "00" * 32,
                "seed",
                Decimal("50"),
                ["first"],
            )


if __name__ == "__main__":
    unittest.main()
