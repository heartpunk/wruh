"""Independent byte oracles for serialized instruction relations and hook state."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from extractor.native_runtime import preload_libstdcxx

preload_libstdcxx()
import z3
from ayxg.codec import loads
from ayxg.z3 import declaration_variables, expr_from_z3, expr_to_z3
from extractor import runtime
from extractor.amd64_state import (
    LTS_EXTRACTION_CONTEXT as CTX,
)
from extractor.amd64_state import (
    _resolve_memory_reads,
    canonical_memory,
    canonical_register,
    claripy_to_z3,
    fresh_instruction_state,
    step_instruction_outcomes,
)
from extractor.binary_cfg import build_static_cfg
from extractor.binary_inventory import PinnedBinary
from extractor.fresh import FreshFunction, extract_fresh_function
from extractor.fresh import artifact_declarations
from extractor.lean_angr_worker import _step

PC = 0x400000
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
            path = Path(directory) / "memory.bin"
            path.write_bytes(raw)
            project = runtime.angr.load_shellcode(raw, arch="amd64", load_address=PC)
            manifest = {
                "image_sha256": hashlib.sha256(raw).hexdigest(),
                "roots": {
                    "memory": {"address": PC, "size": len(raw), "symbol": "memory"}
                },
                "primitive_boundaries": {},
                "call_graph": {"memory": {}},
                "open_transfers": True,
            }
            pinned = PinnedBinary(path, manifest, project)
            function = extract_fresh_function(
                pinned, build_static_cfg(pinned), "memory"
            )
            function = FreshFunction.from_data(json.loads(function.canonical_json()))
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
        project = runtime.angr.load_shellcode(code, arch="amd64", load_address=PC)
        family = step_instruction_outcomes(project, PC)
        self.assertEqual(len(family.outcomes), 1)
        writes = family.outcomes[0].writes
        self.assertEqual(len(writes), 1)
        self.assertIsNotNone(writes[0].condition)
        memory = canonical_memory()
        address = canonical_register("r9")
        old = z3.Concat(*(z3.Select(memory, address + i) for i in (3, 2, 1, 0)))
        expected = z3.Extract(31, 0, canonical_register("rax"))
        self.prove(writes[0].condition == (old == expected), "write condition")

    def test_concrete_write_conditions(self):
        project = runtime.angr.load_shellcode(b"\x90", arch="amd64", load_address=PC)
        address = runtime.claripy.BVV(0x1000, 64)
        memory = canonical_memory()
        destination = z3.BitVecVal(0x1000, 64, CTX)
        for condition, enabled in (
            (True, True),
            (False, False),
            (runtime.claripy.BoolV(True), True),
            (runtime.claripy.BoolV(False), False),
        ):
            with self.subTest(condition=condition):
                state = fresh_instruction_state(project, PC)
                state.memory.store(
                    address, runtime.claripy.BVV(7, 8), size=1, condition=condition
                )
                post = _resolve_memory_reads(
                    state.globals["_ghot_memory_expr"],
                    state.globals["_ghot_memory_reads"],
                )
                expected = z3.Store(memory, destination, z3.BitVecVal(7, 8, CTX)) if enabled else memory
                self.prove(post == expected, "concrete condition")

    def test_lean_worker_preserves_conditional_write(self):
        project = runtime.angr.load_shellcode(
            bytes.fromhex("f0410fb109"), arch="amd64", load_address=PC
        )
        response = _step(SimpleNamespace(project=project), PC)
        dag = response["expression_dag"]
        roots = loads(json.dumps({
            "schema": "ayxg-artifact-dag-v1",
            "expression_dag": dag,
            "payload": [{"$expr": i} for i in range(len(dag["roots"]))],
        }))
        declarations = artifact_declarations(project.arch)
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

    def test_hook_overlap_nested_reads_and_fixed_inputs(self):
        # Real hooked Angr memory operations; oracle uses literal bytes and SMT
        # selects, never production load_le/store_le to compute expectations.
        project = runtime.angr.load_shellcode(b"\x90", arch="amd64", load_address=PC)
        state = fresh_instruction_state(project, PC)
        p = runtime.claripy.BVS("rdi", 64, explicit_name=True)
        q = runtime.claripy.BVS("rsi", 64, explicit_name=True)
        before = state.memory.load(p, 2, endness="Iend_LE")
        state.memory.store(
            p, runtime.claripy.BVV(0xDE42A713, 32), size=4, endness="Iend_LE"
        )
        state.memory.store(
            p + 1, runtime.claripy.BVV(0xBC81, 16), size=2, endness="Iend_LE"
        )
        after = state.memory.load(q, 4, endness="Iend_LE")
        nested = state.memory.load(before.zero_extend(48), 1)
        reads = state.globals["_ghot_memory_reads"]
        resolve = lambda x: _resolve_memory_reads(claripy_to_z3(x), reads)
        m, a, b = (
            canonical_memory(),
            canonical_register("rdi"),
            canonical_register("rsi"),
        )
        old = z3.Concat(z3.Select(m, a + 1), z3.Select(m, a))
        self.prove(resolve(before) == old, "read before writes")
        self.assertEqual(self.result(a == b), z3.sat, "alias witness")
        self.assertEqual(
            self.result(z3.And(a == 0x1003, b == 0x2005)), z3.sat, "nonalias witness"
        )
        self.prove(
            z3.Implies(a == b, resolve(after) == 0xDEBC8113),
            "overlap and symbolic alias",
        )
        self.prove(
            z3.Implies(
                z3.And(*(b + i != a + j for i in range(4) for j in range(4))),
                resolve(after)
                == z3.Concat(*(z3.Select(m, b + i) for i in (3, 2, 1, 0))),
            ),
            "symbolic nonalias",
        )
        # Nested pointer is a 16-bit load zero-extended to the machine address.
        expected_memory = z3.Store(
            z3.Store(
                z3.Store(
                    z3.Store(m, a, z3.BitVecVal(0x13, 8, CTX)),
                    a + 1,
                    z3.BitVecVal(0x81, 8, CTX),
                ),
                a + 2,
                z3.BitVecVal(0xBC, 8, CTX),
            ),
            a + 3,
            z3.BitVecVal(0xDE, 8, CTX),
        )
        self.prove(
            resolve(nested) == z3.Select(expected_memory, z3.ZeroExt(48, old)),
            "nested read uses updated memory",
        )
        fixed = fresh_instruction_state(project, PC)
        fixed.globals["_ghot_fixed_byte_reads"] = tuple(
            (a + i, byte) for i, byte in enumerate(BYTES[:4])
        )
        full = fixed.memory.load(p, 4, endness="Iend_LE")
        partial = fixed.memory.load(p + 2, 4, endness="Iend_LE")
        self.assertEqual(full.op, "BVV")
        self.assertEqual(full.args[0], 0xDE42A713)
        self.assertTrue(partial.symbolic, "partially unknown read must remain symbolic")
        self.assertEqual(
            fixed.globals["_ghot_memory_read_counts"], {"fixed": 1, "symbolic": 1}
        )
        partial_value = _resolve_memory_reads(
            claripy_to_z3(partial), fixed.globals["_ghot_memory_reads"]
        )
        self.prove(
            partial_value == z3.Concat(*(z3.Select(m, a + i) for i in (5, 4, 3, 2))),
            "partial read retains canonical memory",
        )


if __name__ == "__main__":
    unittest.main()
