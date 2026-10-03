"""Static lifting checks; no candidate code is executed natively."""
from __future__ import annotations
import json
from pathlib import Path
from extractor.runtime_trace import start_runtime_trace
start_runtime_trace()
from extractor import runtime
import z3
from extractor.amd64_state import (AMD64_LAYOUT, FLAG_NAMES, LTS_EXTRACTION_CONTEXT as CTX,
    canonical_declarations, canonical_flag, canonical_register, step_instruction_outcomes)
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
    records.append({"case": "layout", "storage": len(AMD64_LAYOUT.storage), "views": len(AMD64_LAYOUT.views)})

    def instruction(name, code):
        family = step_instruction_outcomes(project(code), 0x400000)
        records.append({"case": name, "outcomes": len(family.outcomes),
                        "updated": [sorted(o.updates) for o in family.outcomes]})
        return family
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
    out = instruction("x87-counter-preserves-high-bits", "d9f7").outcomes[0]
    prove(out.updates["ftop"] == canonical_register("ftop") + 1)
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
