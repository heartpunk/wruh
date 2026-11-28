"""Independent byte oracles for serialized instruction relations and hook state."""

from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace

from extractor.native_runtime import preload_libstdcxx

preload_libstdcxx()
import z3
from ayxg.codec import loads
from ayxg.z3 import declaration_variables, expr_from_z3, expr_to_z3
from extractor.elf_fixture import PC, code_session, code_inventory
from extractor.fresh import FreshInstructions, extract_linear, linear_site_records
from extractor.lean_equanimity_worker import _step

# Independent architectural storage roster, not obtained from emitted declarations.
NAMES = (
    {
        "rax",
        "rcx",
        "rdx",
        "rbx",
        "rsp",
        "rbp",
        "rsi",
        "rdi",
        "r8",
        "r9",
        "r10",
        "r11",
        "r12",
        "r13",
        "r14",
        "r15",
        "d",
        "rip",
        "ac",
        "id",
        "fs",
        "sseround",
        "cr0",
        "cr2",
        "cr3",
        "cr4",
        "cr8",
        "k0",
        "k1",
        "k2",
        "k3",
        "k4",
        "k5",
        "k6",
        "k7",
        "fptag",
        "fpround",
        "fc3210",
        "cmstart",
        "cmlen",
        "nraddr",
        "gs",
        "ip_at_syscall",
        "fpreg",
        "ftop",
        "emnote",
        "cs_seg",
        "ds_seg",
        "es_seg",
        "fs_seg",
        "gs_seg",
        "ss_seg",
        "mem",
    }
    | {f"zmm{i}" for i in range(32)}
    | {f"rflags_{n}" for n in ("CF", "ZF", "SF", "OF", "PF", "AF")}
)
BYTES = (0x13, 0xA7, 0x42, 0xDE, 0x81, 0x09, 0xBC, 0x65)
VALUES = {1: 0x13, 2: 0xA713, 4: 0xDE42A713, 8: 0x65BC0981DE42A713}


class MemorySemantics(unittest.TestCase):
    def result(self, expression):
        solver = z3.Solver(ctx=expression.ctx)
        solver.set(timeout=5000)
        solver.add(expression)
        result = solver.check()
        if result == z3.unknown:
            raise RuntimeError(f"INCOMPLETE: {solver.reason_unknown()}")
        return result

    def prove(self, expression, label):
        self.assertEqual(self.result(z3.Not(expression)), z3.unsat, label)

    def extract(self, code):
        raw = bytes.fromhex(code + "c3")
        with tempfile.TemporaryDirectory() as directory:
            session = code_session(directory, raw)
            records = linear_site_records(code_inventory(session, len(raw)), chunk_size=2, seed=7)
            function = extract_linear(session, records)
            function = FreshInstructions.from_data(json.loads(function.canonical_json()))
        self.assertEqual(
            [o.origin.canonical_address for o in function.occurrences],
            [PC, PC + len(raw) - 1],
        )
        edges = [e for e in function.local_edges if e.source == PC]
        self.assertEqual(len(edges), 1, "one instruction outcome")
        ctx = z3.Context()
        variables = declaration_variables(function.declarations, ctx)
        self.assertEqual(set(variables), NAMES, "declaration roster")
        widths = {name: 64 for name in NAMES - {"mem"}}
        widths.update({f"zmm{i}": 512 for i in range(32)})
        widths.update({"fpreg": 512, "ftop": 32, "emnote": 32})
        widths.update(
            {
                name: 16
                for name in ("cs_seg", "ds_seg", "es_seg", "fs_seg", "gs_seg", "ss_seg")
            }
        )
        widths.update(
            {f"rflags_{name}": 1 for name in ("CF", "ZF", "SF", "OF", "PF", "AF")}
        )
        expected_sorts = {
            name: z3.BitVecSort(width, ctx) for name, width in widths.items()
        }
        expected_sorts["mem"] = z3.ArraySort(
            z3.BitVecSort(64, ctx), z3.BitVecSort(8, ctx)
        )
        self.assertEqual(
            {name: variable.sort() for name, variable in variables.items()},
            expected_sorts,
            "independent state sorts",
        )
        return function, edges[0].summary, variables, ctx

    def check(self, function, summary, v, ctx, changes, domain):
        summary.validate(function.declarations)
        convert = lambda x: expr_to_z3(x, v, ctx)
        guard = convert(summary.guard)
        self.prove(guard == (v["rip"] == PC), "exact guard")
        self.assertEqual(
            self.result(z3.And(guard, domain)), z3.sat, "nonvacuous witness"
        )
        post = {a.name: convert(a.value) for a in summary.simultaneous_update}
        self.assertEqual(set(post), NAMES, "complete update roster")
        self.assertEqual(summary.target.kind, "address")
        next_pc = function.occurrences[1].origin.canonical_address
        self.assertEqual(summary.target.value, next_pc)
        self.prove(convert(summary.mirrored_pc) == next_pc, "mirrored PC")
        expected = {**v, **changes, "rip": next_pc}
        self.prove(
            z3.Implies(
                z3.And(guard, domain),
                z3.And(*(post[name] == expected[name] for name in sorted(NAMES))),
            ),
            "complete poststate",
        )

    def test_real_loads(self):
        checked = []
        for size, code in ((1, "8a07"), (2, "668b07"), (4, "8b07"), (8, "488b07")):
            with self.subTest(size=size):
                f, s, v, c = self.extract(code)
                address = v["rdi"]
                domain = z3.And(
                    *(
                        z3.Select(v["mem"], address + i) == byte
                        for i, byte in enumerate(BYTES[:size])
                    )
                )
                expected = z3.BitVecVal(VALUES[size], 64, c)
                if size < 4:
                    expected = (v["rax"] & ~((1 << (size * 8)) - 1)) | expected
                self.check(f, s, v, c, {"rax": expected}, domain)
                # Unaligned and wraparound witnesses must remain feasible.
                self.assertEqual(self.result(z3.And(domain, address == 0x1003)), z3.sat)
                self.assertEqual(
                    self.result(z3.And(domain, address == (1 << 64) - 2)), z3.sat
                )

                checked.append(size)
        self.assertEqual(checked, [1, 2, 4, 8], "all load widths checked")

    def test_real_stores(self):
        checked = []
        for size, code in ((1, "8807"), (2, "668907"), (4, "8907"), (8, "488907")):
            with self.subTest(size=size):
                f, s, v, c = self.extract(code)
                expected = v["mem"]
                for offset, byte in enumerate(BYTES[:size]):
                    expected = z3.Store(
                        expected, v["rdi"] + offset, z3.BitVecVal(byte, 8, c)
                    )
                self.check(f, s, v, c, {"mem": expected}, v["rax"] == VALUES[8])
                post = next(a.value for a in s.simultaneous_update if a.name == "mem")
                memory = expr_to_z3(post, v, c)
                probe = z3.BitVec("probe", 64, c)
                nonalias = z3.And(*(probe != v["rdi"] + i for i in range(size)))
                self.prove(
                    z3.Implies(
                        nonalias, z3.Select(memory, probe) == z3.Select(v["mem"], probe)
                    ),
                    "untouched symbolic address",
                )

                checked.append(size)
        self.assertEqual(checked, [1, 2, 4, 8], "all store widths checked")

    def test_conditional_cmpxchg_stores(self):
        # Compare both paths over an arbitrary memory array, including bytes
        # outside the destination. The inputs are real x86 instruction bytes.
        for code, size in (
            ("f0410fb109", 4),
            ("f00fc70f", 8),
        ):
            with self.subTest(code=code):
                _, summary, variables, ctx = self.extract(code)
                guard = expr_to_z3(summary.guard, variables, ctx)
                memory = variables["mem"]
                address = variables["r9"] if size == 4 else variables["rdi"]
                old = z3.Concat(
                    *(z3.Select(memory, address + i) for i in reversed(range(size)))
                )
                if size == 4:
                    expected = z3.Extract(31, 0, variables["rax"])
                    desired = z3.Extract(31, 0, variables["rcx"])
                else:
                    expected = z3.Concat(
                        z3.Extract(31, 0, variables["rdx"]),
                        z3.Extract(31, 0, variables["rax"]),
                    )
                    desired = z3.Concat(
                        z3.Extract(31, 0, variables["rcx"]),
                        z3.Extract(31, 0, variables["rbx"]),
                    )
                post = expr_to_z3(
                    next(a.value for a in summary.simultaneous_update if a.name == "mem"),
                    variables,
                    ctx,
                )
                stored = memory
                for i in range(size):
                    stored = z3.Store(
                        stored, address + i, z3.Extract(8 * i + 7, 8 * i, desired)
                    )
                for label, branch, expected_memory in (
                    ("success", old == expected, stored),
                    ("failure", old != expected, memory),
                ):
                    self.assertEqual(self.result(z3.And(guard, branch)), z3.sat)
                    self.prove(
                        z3.Implies(z3.And(guard, branch), post == expected_memory),
                        f"{code} memory after {label}",
                    )

    def test_conditional_write_metadata(self):
        code = bytes.fromhex("f0410fb109")
        session = code_session(self.enterContext(tempfile.TemporaryDirectory()), code)
        family = session.step(PC)
        self.assertEqual(len(family.outcomes), 1)
        writes = family.outcomes[0].writes
        self.assertEqual(len(writes), 1)
        self.assertIsNotNone(writes[0].condition)
        ctx = z3.Context()
        variables = declaration_variables(session.image.declarations, ctx)
        memory, address = variables["mem"], variables["r9"]
        old = z3.Concat(*(z3.Select(memory, address + i) for i in (3, 2, 1, 0)))
        expected = z3.Extract(31, 0, variables["rax"])
        self.prove(expr_to_z3(writes[0].condition, variables, ctx) == (old == expected), "write condition")

    def test_overlapping_movsd_reads_before_writing(self):
        session = code_session(self.enterContext(tempfile.TemporaryDirectory()), bytes.fromhex("a5"))
        family = session.step(PC)
        ctx = z3.Context()
        variables = declaration_variables(session.image.declarations, ctx)
        memory, src, dst = (variables[name] for name in ("mem", "rsi", "rdi"))
        expected = memory
        for index in range(4):
            expected = z3.Store(expected, dst + index, z3.Select(memory, src + index))
        self.assertTrue(family.outcomes)
        for item in family.outcomes:
            guard = expr_to_z3(item.guard, variables, ctx)
            post = expr_to_z3(item.updates["mem"], variables, ctx)
            self.prove(z3.Implies(guard, post == expected), "source bytes precede all destination writes")
            for displacement in (0, 1, 8):
                self.assertEqual(self.result(z3.And(guard, dst == src + displacement)), z3.sat)

    def test_lean_worker_preserves_conditional_write(self):
        session = code_session(self.enterContext(tempfile.TemporaryDirectory()), bytes.fromhex("f0410fb109"))
        response = _step(session, PC)
        dag = response["expression_dag"]
        roots = loads(json.dumps({
            "schema": "ayxg-artifact-dag-v1",
            "expression_dag": dag,
            "payload": [{"$expr": i} for i in range(len(dag["roots"]))],
        }))
        declarations = session.image.declarations
        ctx = z3.Context()
        variables = declaration_variables(declarations, ctx)
        self.assertEqual(len(response["outcomes"]), 1)
        outcome = response["outcomes"][0]
        guard = z3.And(
            expr_to_z3(roots[response["source_guard"]], variables, ctx),
            expr_to_z3(roots[outcome["guard"]], variables, ctx),
        )
        mem_index = next(i for i, d in enumerate(declarations) if d.name == "mem")
        post = expr_to_z3(roots[outcome["updates"][mem_index]], variables, ctx)
        memory, address = variables["mem"], variables["r9"]
        old = z3.Concat(*(z3.Select(memory, address + i) for i in (3, 2, 1, 0)))
        expected = z3.Extract(31, 0, variables["rax"])
        desired = z3.Extract(31, 0, variables["rcx"])
        stored = memory
        for i in range(4):
            stored = z3.Store(stored, address + i, z3.Extract(8 * i + 7, 8 * i, desired))
        for label, branch, result in (
            ("success", old == expected, stored),
            ("failure", old != expected, memory),
        ):
            self.assertEqual(self.result(z3.And(guard, branch)), z3.sat)
            self.prove(z3.Implies(z3.And(guard, branch), post == result), label)

    def test_corruptions_are_rejected(self):
        f, s, v, c = self.extract("488b07")
        domain = z3.And(
            *(z3.Select(v["mem"], v["rdi"] + i) == byte for i, byte in enumerate(BYTES))
        )
        rejected = []
        for field, value in (
            ("rax", z3.BitVecVal(0, 64, c)),
            ("rbx", v["rbx"] + 1),
            ("mem", z3.Store(v["mem"], v["rdi"], z3.BitVecVal(0, 8, c))),
        ):
            corrupt = replace(
                s,
                simultaneous_update=tuple(
                    replace(a, value=expr_from_z3(value)) if a.name == field else a
                    for a in s.simultaneous_update
                ),
            )
            with self.assertRaisesRegex(AssertionError, "complete poststate"):
                self.check(
                    f, corrupt, v, c, {"rax": z3.BitVecVal(VALUES[8], 64, c)}, domain
                )

            rejected.append(field)
        self.assertEqual(rejected, ["rax", "rbx", "mem"], "all corruption controls ran")
        with self.assertRaisesRegex(AssertionError, "nonvacuous witness"):
            self.check(
                f,
                s,
                v,
                c,
                {"rax": z3.BitVecVal(VALUES[8], 64, c)},
                z3.BoolVal(False, c),
            )
        with self.assertRaisesRegex(AssertionError, "exact guard"):
            self.check(
                f,
                replace(s, guard=expr_from_z3(z3.BoolVal(False, c))),
                v,
                c,
                {"rax": z3.BitVecVal(VALUES[8], 64, c)},
                domain,
            )

if __name__ == "__main__":
    unittest.main()
