"""Real AMD64 bytes must survive CFG extraction and artifact serialization.

These are instruction-relation tests, not native executions or composition tests.
The manifest deliberately selects small shellcode functions; the production CFG
builder, instruction stepper, fresh extractor, and artifact codec do the work.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import tempfile
import unittest
from pathlib import Path

from extractor.native_runtime import preload_libstdcxx

preload_libstdcxx()
import z3
from ayxg.z3 import declaration_variables, expr_to_z3

from extractor import runtime
from extractor.binary_cfg import build_static_cfg
from extractor.binary_inventory import PinnedBinary
from extractor.fresh import FreshFunction, extract_fresh_function

PC = 0x400000


class InstructionOutcomesTest(unittest.TestCase):
    def assert_unsat(self, expression, label):
        solver = z3.Solver(ctx=expression.ctx)
        solver.set(timeout=5000)
        solver.add(expression)
        result = solver.check()
        detail = solver.model() if result == z3.sat else solver.reason_unknown()
        self.assertEqual(result, z3.unsat, f"{label}: {result}: {detail}")

    def extract(self, code, offsets):
        """Decode a real function ending in RET, then round-trip its artifact."""
        raw = bytes.fromhex(code)
        digest = hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "instruction.bin"
            artifact.write_bytes(raw)
            project = runtime.angr.load_shellcode(raw, arch="amd64", load_address=PC)
            manifest = {
                "image_sha256": digest,
                "roots": {"fixture": {"address": PC, "size": len(raw), "symbol": "fixture"}},
                "primitive_boundaries": {},
                "call_graph": {"fixture": {}},
                "open_transfers": True,
            }
            pinned = PinnedBinary(artifact, manifest, project)
            cfg = build_static_cfg(pinned)
            extracted = extract_fresh_function(pinned, cfg, "fixture")
            function = FreshFunction.from_data(json.loads(extracted.canonical_json()))
        self.assertEqual(function.entry, PC)
        self.assertEqual(function.function_id, "fixture")
        self.assertEqual([o.origin.canonical_address for o in function.occurrences],
                         [PC + offset for offset in offsets])
        self.assertEqual({edge.source for edge in function.local_edges},
                         {PC + offset for offset in offsets})
        for occurrence, start, stop in zip(function.occurrences, offsets, [*offsets[1:], len(raw)]):
            self.assertEqual(occurrence.origin.image_sha256, digest)
            self.assertEqual(occurrence.origin.instruction_bytes, raw[start:stop].hex())
            self.assertEqual(occurrence.origin.function_owners, ("fixture",))
        ctx = z3.Context()
        variables = declaration_variables(function.declarations, ctx)
        edges = [edge for edge in function.local_edges if edge.source == PC]
        return function, edges, variables, ctx

    def check_relation(self, function, edges, variables, ctx, expected, *,
                       domain=None, ignored=frozenset()):
        """Expected tuples are (guard, target, changed state); all else is identity.

        Guards include the source PC. Their union is exact, each expected case
        must have a SAT witness, and state equality holds throughout the stated
        domain. No expected guard or state is calculated from extracted output.
        """
        domain = z3.BoolVal(True, ctx=ctx) if domain is None else domain
        convert = lambda expression: expr_to_z3(expression, variables, ctx)
        guards = [convert(edge.summary.guard) for edge in edges]
        self.assertEqual(len(edges), len(expected), "missing or extra outcome")
        self.assert_unsat(z3.Xor(z3.Or(*guards), z3.Or(*(case[0] for case in expected))),
                          "exact guard coverage")
        for left, right in itertools.combinations(guards, 2):
            self.assert_unsat(z3.And(left, right), "overlapping outcomes")
        for guard, target, changes in expected:
            witness = z3.Solver(ctx=ctx)
            witness.set(timeout=5000)
            witness.add(guard, domain)
            self.assertEqual(witness.check(), z3.sat, "expected outcome has no witness")
            matching = []
            for edge, actual_guard in zip(edges, guards):
                solver = z3.Solver(ctx=ctx)
                solver.set(timeout=5000)
                solver.add(z3.Xor(guard, actual_guard))
                if solver.check() == z3.unsat:
                    matching.append(edge)
            self.assertEqual(len(matching), 1, "missing exact expected guard")
            summary = matching[0].summary
            summary.validate(function.declarations)
            assignments = {item.name: convert(item.value) for item in summary.simultaneous_update}
            self.assertEqual(set(assignments), set(variables), "incomplete state update")
            expected_pc = PC if target == "error" else target
            if target == "error":
                self.assertEqual(summary.target.kind, "error")
            else:
                self.assertEqual(summary.target.kind, "address")
                self.assertEqual(summary.target.value, target)
            self.assert_unsat(z3.And(guard, domain, convert(summary.mirrored_pc) != expected_pc),
                              "wrong mirrored PC")
            expected_state = {**variables, **changes, "rip": expected_pc}
            for name, actual in assignments.items():
                if name not in ignored:
                    self.assert_unsat(z3.And(guard, domain, actual != expected_state[name]),
                                      f"wrong {name} update")

    def test_eax_write_zero_extends_and_preserves_other_state(self):
        function, edges, v, ctx = self.extract("b878563412c3", [0, 5])
        self.check_relation(function, edges, v, ctx,
                            [(v["rip"] == PC, PC + 5, {"rax": 0x12345678})])

    def test_partial_register_write_preserves_other_bits(self):
        function, edges, v, ctx = self.extract("b47fc3", [0, 2])
        expected_rax = (v["rax"] & 0xffffffffffff00ff) | 0x7f00
        self.check_relation(function, edges, v, ctx,
                            [(v["rip"] == PC, PC + 2, {"rax": expected_rax})])

    def test_conditional_branch_retains_both_feasible_targets(self):
        # JE +2; NOP; NOP; RET: both arms have real decoded instructions.
        function, edges, v, ctx = self.extract("74029090c3", [0, 2, 3, 4])
        self.check_relation(function, edges, v, ctx, [
            (z3.And(v["rip"] == PC, v["rflags_ZF"] == 1), PC + 4, {}),
            (z3.And(v["rip"] == PC, v["rflags_ZF"] == 0), PC + 2, {}),
        ])

    def test_division_retains_normal_and_zero_divisor_fault(self):
        function, edges, v, ctx = self.extract("f7f1c3", [0, 2])  # DIV ECX
        eax, edx, ecx = (z3.Extract(31, 0, v[name]) for name in ("rax", "rdx", "rcx"))
        # EDX=0 excludes quotient overflow, which this provider does not model.
        # DIV's arithmetic flags are undefined and have no preservation oracle.
        ignored = frozenset(f"rflags_{name}" for name in ("CF", "PF", "AF", "ZF", "SF", "OF"))
        numerator = z3.Concat(edx, eax)
        divisor = z3.ZeroExt(32, ecx)
        self.check_relation(function, edges, v, ctx, [
            (z3.And(v["rip"] == PC, ecx == 0), "error", {}),
            (z3.And(v["rip"] == PC, ecx != 0), PC + 2, {
                "rax": z3.ZeroExt(32, z3.Extract(31, 0, z3.UDiv(numerator, divisor))),
                "rdx": z3.ZeroExt(32, z3.Extract(31, 0, z3.URem(numerator, divisor))),
            }),
        ], domain=edx == 0, ignored=ignored)

    def test_movsb_retains_both_directions_and_exact_memory_store(self):
        function, edges, v, ctx = self.extract("a4c3", [0, 1])
        memory = z3.Store(v["mem"], v["rdi"], z3.Select(v["mem"], v["rsi"]))
        self.check_relation(function, edges, v, ctx, [
            (z3.And(v["rip"] == PC, v["d"] == direction), PC + 1,
             {"rsi": v["rsi"] + direction, "rdi": v["rdi"] + direction, "mem": memory})
            for direction in (1, -1)
        ])

    def check_rounding_store(self, code, length, selector, shift, fixed_bits, size):
        function, edges, v, ctx = self.extract(code + "c3", [0, length])
        cases = []
        for mode in range(4):
            # VEX's supported control-word representation: masked exceptions,
            # with only the rounding selector varying. Compare the entire array,
            # including untouched neighboring bytes, not just the stored value.
            value = fixed_bits | (mode << shift)
            memory = v["mem"]
            for offset in range(size):
                memory = z3.Store(memory, v["rdi"] + offset,
                                  z3.BitVecVal((value >> (8 * offset)) & 0xff, 8, ctx=ctx))
            cases.append((z3.And(v["rip"] == PC, v[selector] == mode), PC + length,
                          {"mem": memory}))
        self.check_relation(function, edges, v, ctx, cases)

    def test_stmxcsr_retains_all_four_rounding_selectors(self):
        self.check_rounding_store("0fae1f", 3, "sseround", 13, 0x1f80, 4)

    def test_fnstcw_retains_all_four_rounding_selectors(self):
        self.check_rounding_store("d93f", 2, "fpround", 10, 0x037f, 2)

    def test_fincstp_partitions_low_bits_without_losing_high_bits(self):
        function, edges, v, ctx = self.extract("d9f7c3", [0, 2])
        self.check_relation(function, edges, v, ctx, [
            (z3.And(v["rip"] == PC, (v["ftop"] & 7) == slot), PC + 2,
             {"ftop": v["ftop"] + 1})
            for slot in range(8)
        ])


if __name__ == "__main__":
    unittest.main()
