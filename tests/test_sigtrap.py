import hashlib
import os
import unittest
import tempfile

import archinfo
from pathlib import Path

from extractor.backend import Session
from extractor.elf_fixture import PC, code_session
from ayxg.expr import TypedExpr
from extractor.artifact import (
    LocalEdge,
    StaticOccurrenceId,
)
from extractor.lean_equanimity_worker import _step
from extractor.instruction_inventory import Span, inventory
from extractor.fresh import (
    _local_edges,
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
        session = code_session(self.enterContext(tempfile.TemporaryDirectory()), b"\xf4")
        family = session.step(PC)
        self.assertEqual(len(family.outcomes), 1)
        outcome = family.outcomes[0]
        self.assertEqual(outcome.jumpkind, "Ijk_SigTRAP")
        self.assertEqual(outcome.fault_kind, "general_protection")
        emitted = _step(session, PC)["outcomes"][0]
        self.assertEqual(emitted["jumpkind"], "Ijk_SigTRAP")
        self.assertEqual(emitted["fault_kind"], "general_protection")
        self.assertEqual(outcome.target_value, PC)
        self.assertTrue(all(outcome.updates[d.name] == TypedExpr.var(d.name, d.sort)
                            for d in session.image.declarations if d.name != "rip"))
        self.assertEqual(
            outcome.updates["rip"].value, PC
        )
        self.assertEqual(outcome.writes, ())

        edges = _local_edges(
            session.image.declarations,
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
        session = code_session(self.enterContext(tempfile.TemporaryDirectory()), b"\xcc")
        family = session.step(PC)
        self.assertEqual(len(family.outcomes), 1)
        outcome = family.outcomes[0]
        self.assertEqual(outcome.jumpkind, "Ijk_SigTRAP")
        self.assertEqual(outcome.fault_kind, "signal_trap")
        emitted = _step(session, PC)["outcomes"][0]
        self.assertEqual(emitted["jumpkind"], "Ijk_SigTRAP")
        self.assertEqual(emitted["fault_kind"], "signal_trap")
        self.assertEqual(outcome.target_value, PC + 1)
        self.assertEqual(
            outcome.updates["rip"].value, PC + 1
        )
        edges = _local_edges(
            session.image.declarations,
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
        session = Session.load(binary)
        obj = session.image.loaded_image["objects"][0]
        start = next(s for s in obj["function_symbols"] if "_start" in s["names"])
        address = obj["mapped_base"] + start["offset"]
        segment = next(s for s in obj["segments"] if s["address"] <= address < s["address"] + s["size"])
        offset = address - segment["address"]
        start_code = bytes.fromhex(segment["bytes"])[offset:offset + start["size"]]
        decoded = inventory([Span(address, start_code, obj["sha256"], obj["mapped_base"])],
                            [], archinfo.ArchAMD64().capstone)
        self.assertFalse(decoded.unexamined or decoded.unresolved)
        hlt_address, = [i.address for i in decoded.decoded if i.mnemonic == "hlt"]
        family = session.step(hlt_address)
        self.assertEqual(len(family.outcomes), 1)
        outcome = family.outcomes[0]
        self.assertEqual(outcome.jumpkind, "Ijk_SigTRAP")
        self.assertEqual(outcome.fault_kind, "general_protection")
        self.assertEqual(outcome.target_value, hlt_address)
        self.assertEqual(
            outcome.updates["rip"].value, hlt_address
        )

        records = linear_site_records(decoded, chunk_size=64, seed=0)
        fresh = extract_linear(session, records)
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
            if assignment.name == "rip"
        )
        self.assertEqual(
            ip_update.value.to_data(),
            hlt_edges[0].summary.mirrored_pc.to_data(),
        )


if __name__ == "__main__":
    unittest.main()
