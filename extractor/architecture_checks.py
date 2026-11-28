"""Static lifting checks; no candidate code is executed natively."""
from __future__ import annotations

import json
from pathlib import Path

from extractor.runtime_trace import start_runtime_trace

start_runtime_trace()

import tempfile
from types import SimpleNamespace

from extractor.elf_fixture import PC, code_session

# ruff: isort: split
import z3

from ayxg.z3 import declaration_variables, expr_to_z3
from extractor.architecture import ArchitectureLayout, NORMALIZED_AMD64_FLAGS

CTX = z3.Context()
FLAG_NAMES = ("CF", "ZF", "SF", "OF", "PF", "AF")


def prove(expression):
    solver = z3.Solver(ctx=CTX)
    solver.add(z3.Not(expression))
    assert solver.check() == z3.unsat, expression


def check():
    records = []
    with tempfile.TemporaryDirectory() as temp:
        image = code_session(temp, b"\x90").image
    layout = ArchitectureLayout.from_data(image.architecture)
    variables = declaration_variables(image.declarations, CTX)
    def register(name):
        return variables[name]

    def view_value(name):
        view = layout.view(name)
        storage = register(view.storage_name)
        if view.size_bytes * 8 == storage.size():
            return storage
        return z3.Extract((view.byte_offset + view.size_bytes) * 8 - 1, view.byte_offset * 8, storage)

    declarations = variables
    assert set(declarations) == ({r.name for r in layout.storage} - NORMALIZED_AMD64_FLAGS |
                                 {f"rflags_{n}" for n in FLAG_NAMES} | {"mem"})
    for name in ("fs", "gs", "fpreg", "fptag", "ftop", "fpround", "sseround"):
        assert name in declarations
    for view in layout.views:
        item = layout.register(view.storage_name)
        assert 0 <= view.byte_offset and view.byte_offset + view.size_bytes <= item.size_bytes
    prove(view_value("eax") == z3.Extract(31,0,register("rax")))
    prove(view_value("ah") == z3.Extract(15,8,register("rax")))
    assert view_value("pc").eq(register("rip"))
    assert type(layout).from_data(json.loads(json.dumps(layout.to_data()))) == layout
    records.append({"case": "layout", "storage": len(layout.storage), "views": len(layout.views)})

    def instruction(name, code):
        with tempfile.TemporaryDirectory() as temp:
            family = code_session(temp, bytes.fromhex(code)).step(PC)
        def as_z3(expr):
            return expr_to_z3(expr, variables, CTX)
        outcomes = tuple(SimpleNamespace(
            guard=as_z3(item.guard), jumpkind=item.jumpkind,
            updates={key: as_z3(value) for key, value in item.updates.items()}
        ) for item in family.outcomes)
        records.append({"case": name, "outcomes": len(outcomes),
                        "updated": [sorted(k for k, v in o.updates.items() if not v.eq(variables[k]))
                                    for o in outcomes]})
        return SimpleNamespace(source_guard=as_z3(family.source_guard), outcomes=outcomes)
    # Exercise real AMD64 IDIV lifting (idiv rcx), including a negative
    # dividend and truncation-toward-zero remainder through the extraction path.
    family = instruction("signed-idiv-quotient-remainder", "48f7f9")
    dividend_low = z3.BitVecVal((1 << 64) - 7, 64, ctx=CTX)
    dividend_high = z3.BitVecVal((1 << 64) - 1, 64, ctx=CTX)
    divisor = z3.BitVecVal(3, 64, ctx=CTX)
    expected_quotient = z3.BitVecVal((1 << 64) - 2, 64, ctx=CTX)
    expected_remainder = z3.BitVecVal((1 << 64) - 1, 64, ctx=CTX)
    normal_outcomes = [
        outcome for outcome in family.outcomes
        if outcome.jumpkind != "Ijk_SigFPE_IntDiv"
    ]
    assert normal_outcomes, "signed IDIV produced no normal outcome"
    initial_operands = (
        register("rax") == dividend_low,
        register("rdx") == dividend_high,
        register("rcx") == divisor,
    )
    matching_outcomes = []
    for outcome in normal_outcomes:
        solver = z3.Solver(ctx=CTX)
        solver.add(family.source_guard, outcome.guard, *initial_operands)
        if solver.check() == z3.sat:
            matching_outcomes.append(outcome)
    assert len(matching_outcomes) == 1, (
        "negative -7 / 3 did not select exactly one normal IDIV outcome"
    )
    outcome = matching_outcomes[0]
    solver = z3.Solver(ctx=CTX)
    solver.add(family.source_guard, outcome.guard, *initial_operands)
    solver.add(z3.Or(
        outcome.updates["rax"] != expected_quotient,
        outcome.updates["rdx"] != expected_remainder,
    ))
    assert solver.check() == z3.unsat, "signed IDIV quotient/remainder changed"
    out = instruction("eax-zero-extension", "b878563412").outcomes[0]
    prove(out.updates["rax"] == 0x12345678)
    out = instruction("ah-preserves-other-bits", "b47f").outcomes[0]
    old = register("rax")
    prove(out.updates["rax"] == ((old & z3.BitVecVal(0xffffffffffff00ff,64,ctx=CTX)) | 0x7f00))
    out = instruction("vector-alias-pxor", "660fefc0").outcomes[0]
    backing = layout.view("xmm0").storage_name
    old = register(backing)
    assert backing in out.updates
    prove(z3.Extract(127,0,out.updates[backing]) == 0)
    if old.size() > 128:
        prove(z3.Extract(old.size()-1,128,out.updates[backing]) == z3.Extract(old.size()-1,128,old))
    out = instruction("fs-parametric-load", "64488b042500000000").outcomes[0]
    assert "fs" in str(out.updates["rax"])
    out = instruction("gs-parametric-load", "65488b042500000000").outcomes[0]
    assert "gs" in str(out.updates["rax"])
    out = instruction("flag-normalization", "f8").outcomes[0]
    prove(out.updates["rflags_CF"] == 0)
    for flag in set(FLAG_NAMES) - {"CF"}:
        prove(out.updates[f"rflags_{flag}"] == variables[f"rflags_{flag}"])
    family = instruction("x87-counter-preserves-high-bits", "d9f7")
    assert len(family.outcomes) == 8
    prove(z3.Or(*(o.guard for o in family.outcomes)))
    for out in family.outcomes:
        prove(z3.Implies(out.guard, out.updates["ftop"] == (register("ftop") + 1)))
    family = instruction("sse-rounding-selector-store", "0fae1f")
    assert len(family.outcomes) == 4
    prove(z3.Or(*(o.guard for o in family.outcomes)) == z3.ULE(register("sseround"),3))
    family = instruction("x87-rounding-selector-store", "d93f")
    assert len(family.outcomes) == 4
    prove(z3.Or(*(o.guard for o in family.outcomes)) == z3.ULE(register("fpround"),3))
    family = instruction("direction-selector-partition", "a4")
    assert len(family.outcomes) == 2
    prove(z3.Or(*(o.guard for o in family.outcomes)) ==
          z3.Or(register("d") == 1, register("d") == (1 << 64) - 1))
    for a,b in zip(family.outcomes, family.outcomes[1:]):
        prove(z3.Not(z3.And(a.guard,b.guard)))
    return {"status": "PASS", "architecture": layout.to_data(), "records": records}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    args = parser.parse_args()
    output = json.dumps(check(), indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(output)
    else:
        print(output)
