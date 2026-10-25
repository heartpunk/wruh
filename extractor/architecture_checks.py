"""Static lifting checks; no candidate code is executed natively."""
from __future__ import annotations

import json
from pathlib import Path

from extractor.runtime_trace import start_runtime_trace

start_runtime_trace()

import z3

from extractor import runtime
from extractor.amd64_state import (
    AMD64_LAYOUT,
    FLAG_NAMES,
    LTS_EXTRACTION_CONTEXT as CTX,
    canonical_declarations,
    canonical_flag,
    canonical_register,
    canonical_register_view,
    step_instruction_outcomes,
)
from extractor.architecture import NORMALIZED_AMD64_FLAGS


def prove(expression):
    solver = z3.Solver(ctx=CTX)
    solver.add(z3.Not(expression))
    assert solver.check() == z3.unsat, expression


def project(code):
    return runtime.angr.load_shellcode(bytes.fromhex(code), arch="amd64", load_address=0x400000)


def check():
    records = []
    declarations = {d.name: d for d in canonical_declarations()}
    assert set(declarations) == ({r.name for r in AMD64_LAYOUT.storage} - NORMALIZED_AMD64_FLAGS |
                                 {f"rflags_{n}" for n in FLAG_NAMES} | {"mem"})
    for name in ("fs", "gs", "fpreg", "fptag", "ftop", "fpround", "sseround"):
        assert name in declarations
    for view in AMD64_LAYOUT.views:
        item = AMD64_LAYOUT.register(view.storage_name)
        assert 0 <= view.byte_offset and view.byte_offset + view.size_bytes <= item.size_bytes
    prove(canonical_register_view("eax") == z3.Extract(31,0,canonical_register("rax")))
    prove(canonical_register_view("ah") == z3.Extract(15,8,canonical_register("rax")))
    assert canonical_register_view("pc").eq(canonical_register("rip"))
    assert type(AMD64_LAYOUT).from_data(json.loads(json.dumps(AMD64_LAYOUT.to_data()))) == AMD64_LAYOUT
    records.append({"case": "layout", "storage": len(AMD64_LAYOUT.storage), "views": len(AMD64_LAYOUT.views)})

    def instruction(name, code):
        family = step_instruction_outcomes(project(code), 0x400000)
        records.append({"case": name, "outcomes": len(family.outcomes),
                        "updated": [sorted(o.updates) for o in family.outcomes]})
        return family
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
        canonical_register("rax") == dividend_low,
        canonical_register("rdx") == dividend_high,
        canonical_register("rcx") == divisor,
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
    old = canonical_register("rax")
    prove(out.updates["rax"] == ((old & z3.BitVecVal(0xffffffffffff00ff,64,ctx=CTX)) | 0x7f00))
    out = instruction("vector-alias-pxor", "660fefc0").outcomes[0]
    backing = AMD64_LAYOUT.view("xmm0").storage_name
    old = canonical_register(backing)
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
        prove(out.updates.get(f"rflags_{flag}", canonical_flag(flag)) == canonical_flag(flag))
    family = instruction("x87-counter-preserves-high-bits", "d9f7")
    assert len(family.outcomes) == 8
    prove(z3.Or(*(o.guard for o in family.outcomes)))
    for out in family.outcomes:
        prove(z3.Implies(out.guard, out.updates["ftop"] == (canonical_register("ftop") + 1)))
    family = instruction("sse-rounding-selector-store", "0fae1f")
    assert len(family.outcomes) == 4
    prove(z3.Or(*(o.guard for o in family.outcomes)) == z3.ULE(canonical_register("sseround"),3))
    family = instruction("x87-rounding-selector-store", "d93f")
    assert len(family.outcomes) == 4
    prove(z3.Or(*(o.guard for o in family.outcomes)) == z3.ULE(canonical_register("fpround"),3))
    family = instruction("direction-selector-partition", "a4")
    assert len(family.outcomes) == 2
    prove(z3.Or(*(o.guard for o in family.outcomes)) ==
          z3.Or(canonical_register("d") == 1, canonical_register("d") == (1 << 64) - 1))
    for a,b in zip(family.outcomes, family.outcomes[1:]):
        prove(z3.Not(z3.And(a.guard,b.guard)))
    return {"status": "PASS", "architecture": AMD64_LAYOUT.to_data(), "records": records}


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
