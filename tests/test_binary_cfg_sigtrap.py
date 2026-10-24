import os
import unittest
from pathlib import Path

from extractor import runtime
from extractor.amd64_state import AMD64_LAYOUT, step_instruction_outcomes
from extractor.artifact import (
    DecodedInstructionEvidence,
    LocalEdge,
    StaticOccurrenceId,
)
from extractor.lean_angr_worker import _step
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

    def test_hlt_sigtrap_is_terminal_fault_outcome(self):
        project = runtime.angr.load_shellcode(
            b"\xf4", arch="amd64", load_address=0x400000
        )

        family = step_instruction_outcomes(project, 0x400000)
        pinned = PinnedBinary(
            artifact=Path("<synthetic-hlt>"),
            manifest={"open_transfers": False},
            project=project,
        )

        self.assertEqual(len(family.outcomes), 1)
        outcome = family.outcomes[0]
        self.assertEqual(outcome.jumpkind, "Ijk_SigTRAP")
        self.assertEqual(outcome.fault_kind, "general_protection")
        emitted = _step(pinned, 0x400000)["outcomes"][0]
        self.assertEqual(emitted["jumpkind"], "Ijk_SigTRAP")
        self.assertEqual(emitted["fault_kind"], "general_protection")
        self.assertEqual(outcome.target_value, 0x400000)
        self.assertEqual(set(outcome.updates), {AMD64_LAYOUT.ip_view})
        self.assertEqual(
            outcome.updates[AMD64_LAYOUT.ip_view].as_long(), 0x400000
        )
        self.assertEqual(outcome.writes, ())

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
        self.assertEqual(edges[0].jumpkind, "Ijk_SigTRAP")
        self.assertEqual(edges[0].fault_kind, "general_protection")
        restored = LocalEdge.from_data(edges[0].to_data())
        self.assertEqual(restored.jumpkind, "Ijk_SigTRAP")
        self.assertEqual(restored.fault_kind, "general_protection")

    def test_int3_sigtrap_keeps_post_instruction_rip(self):
        project = runtime.angr.load_shellcode(
            b"\xcc", arch="amd64", load_address=0x400000
        )

        family = step_instruction_outcomes(project, 0x400000)
        pinned = PinnedBinary(
            artifact=Path("<synthetic-int3>"),
            manifest={"open_transfers": False},
            project=project,
        )

        self.assertEqual(len(family.outcomes), 1)
        outcome = family.outcomes[0]
        self.assertEqual(outcome.jumpkind, "Ijk_SigTRAP")
        self.assertEqual(outcome.fault_kind, "signal_trap")
        emitted = _step(pinned, 0x400000)["outcomes"][0]
        self.assertEqual(emitted["jumpkind"], "Ijk_SigTRAP")
        self.assertEqual(emitted["fault_kind"], "signal_trap")
        self.assertEqual(outcome.target_value, 0x400001)
        self.assertEqual(
            outcome.updates[AMD64_LAYOUT.ip_view].as_long(), 0x400001
        )
        edges = _local_edges(
            artifact_declarations(project.arch),
            StaticOccurrenceId(0),
            family,
        )
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].summary.target.kind, "error")
        self.assertEqual(edges[0].jumpkind, "Ijk_SigTRAP")
        self.assertEqual(edges[0].fault_kind, "signal_trap")
        restored = LocalEdge.from_data(edges[0].to_data())
        self.assertEqual(restored.jumpkind, "Ijk_SigTRAP")
        self.assertEqual(restored.fault_kind, "signal_trap")

    @unittest.skipUnless(
        os.environ.get("WRUH_APACHE_HTTPD"),
        "WRUH_APACHE_HTTPD must point to the pinned Apache httpd binary",
    )
    def test_apache_start_hlt_keeps_sigtrap_provenance_and_gp_fault(self):
        project = runtime.angr.Project(
            os.environ["WRUH_APACHE_HTTPD"], auto_load_libs=False
        )
        start_symbol = project.loader.main_object.get_symbol("_start")
        self.assertIsNotNone(start_symbol)

        start_block = project.factory.block(
            start_symbol.rebased_addr, num_inst=64
        )
        hlt_instructions = [
            instruction
            for instruction in start_block.capstone.insns
            if instruction.mnemonic == "hlt"
        ]
        self.assertEqual(len(hlt_instructions), 1)
        hlt_address = hlt_instructions[0].address

        family = step_instruction_outcomes(project, hlt_address)
        self.assertEqual(len(family.outcomes), 1)
        outcome = family.outcomes[0]
        self.assertEqual(outcome.jumpkind, "Ijk_SigTRAP")
        self.assertEqual(outcome.fault_kind, "general_protection")
        self.assertEqual(outcome.target_value, hlt_address)
        self.assertEqual(
            outcome.updates[AMD64_LAYOUT.ip_view].as_long(), hlt_address
        )


if __name__ == "__main__":
    unittest.main()
