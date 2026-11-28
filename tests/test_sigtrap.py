import hashlib
import os
import unittest
from pathlib import Path

from extractor import runtime
from extractor.amd64_state import AMD64_LAYOUT, step_instruction_outcomes
from extractor.artifact import (
    LocalEdge,
    StaticOccurrenceId,
)
from extractor.lean_angr_worker import _step
from extractor.instruction_inventory import Span, inventory
from extractor.fresh import (
    _local_edges,
    artifact_declarations,
    extract_linear,
    linear_site_records,
)


class SigtrapAdapterTest(unittest.TestCase):
    # Nixpkgs Apache 2.4.71 from flake.lock; inspect the installed binary without
    # copying its glibc CRT startup bytes into this repository.
    APACHE_HTTPD_SHA256 = (
        "36399fd28157325004304f84f77a5f777250fb7fc26afdc025b75c2fea07e700"
    )

    def test_hlt_sigtrap_is_terminal_fault_outcome(self):
        project = runtime.angr.load_shellcode(
            b"\xf4", arch="amd64", load_address=0x400000
        )

        family = step_instruction_outcomes(project, 0x400000)
        self.assertEqual(len(family.outcomes), 1)
        outcome = family.outcomes[0]
        self.assertEqual(outcome.jumpkind, "Ijk_SigTRAP")
        self.assertEqual(outcome.fault_kind, "general_protection")
        emitted = _step(project, 0x400000)["outcomes"][0]
        self.assertEqual(emitted["jumpkind"], "Ijk_SigTRAP")
        self.assertEqual(emitted["fault_kind"], "general_protection")
        self.assertEqual(outcome.target_value, 0x400000)
        self.assertEqual(set(outcome.updates), {AMD64_LAYOUT.ip_view})
        self.assertEqual(
            outcome.updates[AMD64_LAYOUT.ip_view].as_long(), 0x400000
        )
        self.assertEqual(outcome.writes, ())

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
        self.assertEqual(len(family.outcomes), 1)
        outcome = family.outcomes[0]
        self.assertEqual(outcome.jumpkind, "Ijk_SigTRAP")
        self.assertEqual(outcome.fault_kind, "signal_trap")
        emitted = _step(project, 0x400000)["outcomes"][0]
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
        binary = Path(os.environ["WRUH_APACHE_HTTPD"])
        self.assertEqual(
            hashlib.sha256(binary.read_bytes()).hexdigest(),
            self.APACHE_HTTPD_SHA256,
            "WRUH_APACHE_HTTPD must be the pinned Nixpkgs Apache 2.4.71 binary",
        )
        project = runtime.angr.Project(binary, auto_load_libs=False)
        start_symbol = project.loader.main_object.get_symbol("_start")
        self.assertIsNotNone(start_symbol)

        start_code = project.loader.memory.load(
            start_symbol.rebased_addr, start_symbol.size
        )
        start_instructions = list(
            project.arch.capstone.disasm(start_code, start_symbol.rebased_addr)
        )
        self.assertTrue(start_instructions)
        self.assertEqual(start_instructions[0].address, start_symbol.rebased_addr)
        self.assertEqual(
            start_instructions[-1].address + start_instructions[-1].size,
            start_symbol.rebased_addr + start_symbol.size,
        )
        hlt_instructions = [
            instruction
            for instruction in start_instructions
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

        image_sha256 = hashlib.sha256(binary.read_bytes()).hexdigest()
        decoded = inventory([Span(start_symbol.rebased_addr, start_code, image_sha256,
                                  project.loader.main_object.mapped_base)], [], project.arch.capstone)
        records = linear_site_records(project, decoded, chunk_size=64, seed=0)
        fresh = extract_linear(project, records)
        hlt_edges = [
            edge for edge in fresh.local_edges if edge.source == hlt_address
        ]
        self.assertEqual(len(hlt_edges), 1)
        self.assertEqual(hlt_edges[0].jumpkind, "Ijk_SigTRAP")
        self.assertEqual(hlt_edges[0].fault_kind, "general_protection")
        self.assertEqual(hlt_edges[0].summary.target.kind, "error")
        ip_update = next(
            assignment
            for assignment in hlt_edges[0].summary.simultaneous_update
            if assignment.name == AMD64_LAYOUT.ip_view
        )
        self.assertEqual(
            ip_update.value.to_data(),
            hlt_edges[0].summary.mirrored_pc.to_data(),
        )


if __name__ == "__main__":
    unittest.main()
