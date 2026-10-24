import unittest
from pathlib import Path

from extractor import runtime
from extractor.amd64_state import AMD64_LAYOUT, step_instruction_outcomes
from extractor.artifact import DecodedInstructionEvidence, StaticOccurrenceId
from extractor.binary_cfg import _walk_function
from extractor.binary_inventory import PinnedBinary
from extractor.fresh import _local_edges, artifact_declarations


class SigtrapAdapterTest(unittest.TestCase):
    def test_decoded_evidence_accepts_elf_entry_symbol_owner(self):
        evidence = DecodedInstructionEvidence(
            image_sha256="0" * 64,
            canonical_address=0x400000,
            instruction_bytes="f4",
            architecture="AMD64",
            decode_mode="default",
            instruction_identity="hlt",
            function_owners=("_start",),
        )

        self.assertEqual(
            DecodedInstructionEvidence.from_data(evidence.to_data()), evidence
        )

    def test_hlt_without_engine_successors_becomes_error_outcome(self):
        project = runtime.angr.load_shellcode(
            b"\xf4", arch="amd64", load_address=0x400000
        )

        family = step_instruction_outcomes(project, 0x400000)

        self.assertEqual(len(family.outcomes), 1)
        outcome = family.outcomes[0]
        self.assertEqual(outcome.jumpkind, "Ijk_SigTRAP")
        self.assertEqual(outcome.target_value, 0x400000)
        self.assertEqual(set(outcome.updates), {AMD64_LAYOUT.ip_view})
        self.assertEqual(
            outcome.updates[AMD64_LAYOUT.ip_view].as_long(), 0x400000
        )
        self.assertEqual(outcome.writes, ())

        pinned = PinnedBinary(
            artifact=Path("<synthetic-hlt>"),
            manifest={"open_transfers": False},
            project=project,
        )
        blocks, calls, indirect_sites = _walk_function(
            pinned,
            root_name="synthetic_hlt",
            root={"address": 0x400000, "size": 1},
            jump_tables={},
        )
        self.assertEqual(calls, [])
        self.assertEqual(indirect_sites, set())
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["instructions"][0]["mnemonic"], "hlt")
        self.assertEqual(blocks[0]["successors"], [])

        edges = _local_edges(
            artifact_declarations(project.arch),
            StaticOccurrenceId(0),
            family,
        )
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].summary.target.kind, "error")


if __name__ == "__main__":
    unittest.main()
