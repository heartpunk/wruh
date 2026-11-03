import unittest
from pathlib import Path
from types import SimpleNamespace

from extractor.binary_census import (
    _candidate_manifest,
    _entry_nodes,
    _function_candidates,
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

    def test_recovered_candidate_records_inferred_extent_and_identity(self):
        candidate = {
            "id": "fn_0000000000001000", "object_virtual_address": 0x1000,
            "size": 0x20, "aliases": [], "identity_basis": "cfgfast",
        }
        nodes, _ = _entry_nodes(
            census_id="urn:test:census", candidate=candidate,
            binary_id="urn:test:binary", disposition="not_attempted",
            attempt_id=None, started=None, ended=None, tool_release_ids=[],
        )
        node = nodes[0]
        self.assertEqual(node["bfe:recoveredExtentBytes"], 0x20)
        self.assertNotIn("bfe:declaredExtentBytes", node)
        self.assertEqual(node["bfe:candidateAliasIdentifier"], [])
        self.assertEqual(node["bfe:candidateIdentityBasis"], [
            {"@id": "bfe:CFGFastEntry"}, {"@id": "bfe:UniqueEntryAddress"},
        ])

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


if __name__ == "__main__":
    unittest.main()
