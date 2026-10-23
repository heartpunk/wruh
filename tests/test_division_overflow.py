"""Unsigned DIV keeps #DE on quotient overflow, without partial writeback.

Guards cover the entire operand domain. Normal-state examples use Python's
integer divmod independently of VEX/Z3 division; undefined success flags are
not prescribed. Memory is the extractor's canonical byte array, not a model
of paging/canonical-address faults. IDIV is a separate, unchanged limitation.
"""

from extractor.native_runtime import preload_libstdcxx

preload_libstdcxx()

import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

import z3
from ayxg.expr import TypedExpr
from ayxg.z3 import declaration_variables, expr_from_z3, expr_to_z3

from extractor import runtime
from extractor.binary_cfg import build_static_cfg
from extractor.binary_inventory import PinnedBinary
from extractor.division import unsigned_divide_irsb
from extractor.fresh import FreshFunction, extract_fresh_function
from extractor.open_transfers_smoke import AMD64_SORTS, complete_solver_result

PC = 0x401000
CASES = ((8, "f6f1", False), (16, "66f7f1", False),
         (32, "f7f1", False), (64, "48f7f1", False),
         (8, "f637", True), (16, "66f737", True),
         (32, "f737", True), (64, "48f737", True))
FLAGS = frozenset(f"rflags_{name}" for name in ("CF", "PF", "AF", "ZF", "SF", "OF"))


class DivisionOverflow(unittest.TestCase):
    def result(self, condition):
        solver = z3.Solver(ctx=condition.ctx)
        solver.set(timeout=5000)
        solver.add(condition)
        return complete_solver_result(solver)

    def prove(self, condition, label):
        self.assertEqual(self.result(z3.Not(condition)), z3.unsat, label)

    def extract(self, code):
        raw = bytes.fromhex(code + "c3")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "division.bin"
            path.write_bytes(raw)
            project = runtime.angr.load_shellcode(raw, arch="amd64", load_address=PC)
            block = project.factory.block(PC, num_inst=1)
            before = str(block.vex)
            first = unsigned_divide_irsb(block)
            second = unsigned_divide_irsb(block)
            self.assertEqual(str(block.vex), before, "cached VEX block unchanged")
            self.assertEqual(str(first), str(second), "repeatable private lift")
            self.assertIsNot(first, second)
            self.assertTrue(first.typecheck(), "well-typed guarded VEX")
            manifest = {"image_sha256": hashlib.sha256(raw).hexdigest(),
                        "roots": {"division": {"address": PC, "size": len(raw), "symbol": "division"}},
                        "primitive_boundaries": {}, "call_graph": {"division": {}},
                        "open_transfers": True}
            pinned = PinnedBinary(path, manifest, project)
            function = extract_fresh_function(pinned, build_static_cfg(pinned), "division")
            function = FreshFunction.from_data(json.loads(function.canonical_json()))
        self.assertEqual([(o.origin.canonical_address, o.origin.instruction_bytes)
                          for o in function.occurrences], [(PC, code), (PC + len(raw) - 1, "c3")])
        return function, PC + len(raw) - 1

    def check(self, function, next_pc, bits, memory):
        ctx = z3.Context()
        self.assertEqual({d.name: d.sort for d in function.declarations}, AMD64_SORTS)
        v = declaration_variables(function.declarations, ctx)
        mask = (1 << bits) - 1
        low = z3.Extract(bits - 1, 0, v["rax"])
        high = z3.Extract(15, 8, v["rax"]) if bits == 8 else z3.Extract(bits - 1, 0, v["rdx"])
        numerator = z3.Concat(high, low)
        if memory:
            values = [z3.Select(v["mem"], v["rdi"] + i) for i in reversed(range(bits // 8))]
            divisor = values[0] if bits == 8 else z3.Concat(*values)
        else:
            divisor = z3.Extract(bits - 1, 0, v["rcx"])
        # Independent full-dividend inequality, rather than the implementation's
        # shifted-high-half comparison. No restriction such as EDX=0 is imposed.
        source = v["rip"] == PC
        limit = z3.ZeroExt(bits, divisor) << bits
        error = z3.And(source, z3.Or(divisor == 0, z3.UGE(numerator, limit)))
        normal = z3.And(source, divisor != 0, z3.ULT(numerator, limit))
        edges = [edge for edge in function.local_edges if edge.source == PC]
        faults = [edge for edge in edges if edge.summary.target.kind == "error"]
        successes = [edge for edge in edges if edge.summary.target.kind == "address"]
        self.assertEqual(len(edges), len(faults) + len(successes))
        self.assertTrue(faults, "fault outcomes present")
        self.assertEqual(len(successes), 1)
        convert = lambda term: expr_to_z3(term, v, ctx)
        guards = [convert(edge.summary.guard) for edge in edges]
        self.prove(z3.Or(*guards) == source, "complete guard partition")
        self.prove(z3.Or(*(convert(edge.summary.guard) for edge in faults)) == error, "exact fault guard")
        self.prove(convert(successes[0].summary.guard) == normal, "exact normal guard")
        checked = []
        for index, guard in enumerate(guards):
            self.assertEqual(self.result(guard), z3.sat, "feasible outcome")
            for other in guards[index + 1:]:
                self.assertEqual(self.result(z3.And(guard, other)), z3.unsat, "disjoint outcomes")
            checked.append(index)
        self.assertEqual(checked, list(range(len(edges))))

        def state(edge, domain, changes, ignored=frozenset()):
            summary = edge.summary
            self.assertIsNone(summary.external_effect)
            actual = {a.name: convert(a.value) for a in summary.simultaneous_update}
            self.assertEqual(set(actual), set(AMD64_SORTS), "complete update roster")
            expected = {**v, **changes}
            guard = convert(summary.guard)
            self.assertEqual(self.result(z3.And(guard, domain)), z3.sat, "state witness")
            self.prove(z3.Implies(z3.And(guard, domain), z3.And(*[
                actual[name] == expected[name] for name in sorted(AMD64_SORTS) if name not in ignored])),
                "complete poststate")
            self.prove(convert(summary.mirrored_pc) == changes["rip"], "mirrored PC")

        checked = []
        for edge in faults:
            state(edge, z3.BoolVal(True, ctx=ctx), {"rip": PC})
            checked.append(edge.id)
        self.assertEqual(checked, [edge.id for edge in faults])
        # Python computes expected results; poison high register bits distinguish
        # 8/16-bit preservation from 32-bit zero extension and 64-bit replacement.
        observed = []
        for hi, lo, den in ((0, 13, 3), (2, mask, 3), (0, 0, mask)):
            quotient, remainder = divmod((hi << bits) | lo, den)
            self.assertLessEqual(quotient, mask)
            rax = (0xA55A123456789ABC & ~((1 << (16 if bits == 8 else bits)) - 1)) | ((hi << 8) | lo if bits == 8 else lo)
            rdx = (0x5AA5FEDCBA987654 & ~mask) | hi
            domain = z3.And(v["rax"] == rax, v["rdx"] == rdx, divisor == den)
            if bits == 8:
                changes = {"rax": (rax & ~0xffff) | (remainder << 8) | quotient}
            elif bits == 16:
                changes = {"rax": (rax & ~mask) | quotient, "rdx": (rdx & ~mask) | remainder}
            else:
                changes = {"rax": quotient, "rdx": remainder}
            self.assertEqual(successes[0].summary.target.value, next_pc)
            state(successes[0], domain, {**changes, "rip": next_pc}, FLAGS)
            observed.append((hi, lo, den))
        self.assertEqual(observed, [(0, 13, 3), (2, mask, 3), (0, 0, mask)])
        # Pin the first overflowing quotient and both ends of the divisor range.
        for den in (1, mask):
            self.assertEqual(self.result(z3.And(error, high == den, low == 0, divisor == den)), z3.sat)
        self.assertEqual(self.result(z3.And(error, high == 0, low == 13, divisor == 0)), z3.sat)

    def test_all_widths_and_operand_kinds(self):
        checked = []
        for bits, code, memory in CASES:
            with self.subTest(bits=bits, memory=memory):
                function, next_pc = self.extract(code)
                self.check(function, next_pc, bits, memory)
                checked.append((bits, memory))
        self.assertEqual(checked, [(8, False), (16, False), (32, False), (64, False),
                                   (8, True), (16, True), (32, True), (64, True)])

    def test_corruptions_are_rejected(self):
        function, next_pc = self.extract("f7f1")
        normal = next(edge for edge in function.local_edges if edge.source == PC and edge.summary.target.kind == "address")
        fault = next(edge for edge in function.local_edges if edge.source == PC and edge.summary.target.kind == "error")
        ctx = z3.Context()
        v = declaration_variables(function.declarations, ctx)
        unbounded = expr_from_z3(z3.And(v["rip"] == PC, z3.Extract(31, 0, v["rcx"]) != 0))
        bad_fault = replace(fault.summary, simultaneous_update=tuple(
            replace(a, value=TypedExpr.bv_lit(64, 0)) if a.name == "rax" else a
            for a in fault.summary.simultaneous_update))
        cases = [("exact normal guard", normal, replace(normal.summary, guard=unbounded)),
                 ("complete poststate", fault, bad_fault)]
        checked = []
        for label, original, summary in cases:
            damaged = replace(function, local_edges=tuple(
                replace(edge, summary=summary) if edge == original else edge for edge in function.local_edges))
            with self.assertRaisesRegex(AssertionError, label):
                self.check(damaged, next_pc, 32, False)
            checked.append(label)
        self.assertEqual(checked, ["exact normal guard", "complete poststate"])


if __name__ == "__main__":
    unittest.main()
