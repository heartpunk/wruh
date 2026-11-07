"""Extract the actual MOV-only ingress bytes, preserving the pinned environment.

The exporter checks that all sixteen updates are reads from their intended
slots and that no other modeled state or memory changes occur. InputModel.lean
contains the checked expression tree and an independently constructed layout.
"""
from pathlib import Path
import hashlib
import sys

from extract_stub import amd, runtime, z3
from stub import GPRS, INPUT, LOAD_CODE, loader_bytes


def emit_expr(e):
    if z3.is_bv_value(e):
        return f"(.bvLit {e.size()} {e.as_long()})"
    kind = e.decl().kind()
    if kind == z3.Z3_OP_UNINTERPRETED:
        assert str(e) == "mem"
        return "(.var v_mem)"
    if kind == z3.Z3_OP_SELECT:
        return f"(.select 64 8 {emit_expr(e.arg(0))} {emit_expr(e.arg(1))})"
    if kind == z3.Z3_OP_CONCAT:
        parts = e.children()
        result, width = emit_expr(parts[0]), parts[0].size()
        for part in parts[1:]:
            result = f"(.concat {width} {part.size()} {result} {emit_expr(part)})"
            width += part.size()
        return result
    raise ValueError(f"unhandled ingress expression: {e.sexpr()}")


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "out")
    encoded = loader_bytes()
    project = runtime.angr.load_shellcode(encoded, arch="amd64", load_address=LOAD_CODE)
    block = project.factory.block(LOAD_CODE, size=len(encoded), num_inst=16)
    assert block.size == len(encoded) and block.vex.instructions == 16
    assert all(i.mnemonic == "mov" and i.size == 7 for i in block.capstone.insns)
    state = amd.fresh_instruction_state(project, LOAD_CODE)
    successors = project.factory.successors(state, size=len(encoded), num_inst=16).all_successors
    assert len(successors) == 1
    post = successors[0]
    assert not post.solver.constraints and post.history.jumpkind == "Ijk_Boring"
    post.globals["_wruh_capture_selectors"] = False
    updates = amd._post_updates(post, LOAD_CODE)
    assert set(updates) == set(GPRS), sorted(updates)
    target, value = amd._symbolic_target_update(post, updates)
    assert value == LOAD_CODE + len(encoded)
    assert not amd._resolved_writes(post)
    assert z3.simplify(post.globals["_ghot_memory_expr"]).eq(amd.canonical_memory())
    for i, name in enumerate(GPRS):
        expected = z3.Concat(*[z3.Select(amd.canonical_memory(),
            z3.BitVecVal(INPUT + 8*i + b, 64, ctx=amd.canonical_memory().ctx))
            for b in reversed(range(8))])
        assert z3.simplify(updates[name]).eq(z3.simplify(expected)), name
    declared = {d.name: d for d in amd.canonical_declarations()}
    names = ["mem", "rip", *GPRS]
    names += [name for name in declared if name not in names]
    lines = ["-- Generated from loader.bin and fresh Wruh extraction.",
             f"-- SHA256 {hashlib.sha256(encoded).hexdigest()}",
             "import Extracted", "set_option maxRecDepth 16384",
             "namespace MovObserver", "open Ayxg.QfAbv"]
    for name in GPRS:
        lines += [f"def load_{name} : Expr Γ (.bv 64) := {emit_expr(z3.simplify(updates[name]))}"]
    terms = ["(.var v_mem)", f"(.bvLit 64 {LOAD_CODE + len(encoded)})"]
    terms += [f"load_{name}" if name in updates else f"(.var v_{name})" for name in names[2:]]
    update = ".nil"
    for term in reversed(terms):
        update = f"(.cons {term}\n  {update})"
    lines += [f"def loadUpdate : StateUpdate Γ Γ := {update}",
              f"def loadGuard : Expr Γ .bool := .eqBv 64 (.var v_rip) (.bvLit 64 {LOAD_CODE})",
              "def loadStep : QFAbvStep Γ Γ := ⟨loadGuard, loadUpdate⟩",
              "variable [FPInterpretation]"]
    for name in names:
        if name in GPRS or name == "rip":
            continue
        lines += [f"theorem loader_preserves_{name} (s : Env Γ) :",
                  f"    Env.lookup (loadUpdate.eval s) v_{name} = Env.lookup s v_{name} := rfl"]
    lines += ["end MovObserver"]
    (out / "loader.bin").write_bytes(encoded)
    (out / "loader-vex.txt").write_text(str(block.vex) + "\n")
    (out / "InputModel.lean").write_text("\n".join(lines) + "\n")
    print(f"PASS: loader bytes={len(encoded)}, sixteen GPR loads, no memory writes, "
          f"all other modeled fields preserved; sha256={hashlib.sha256(encoded).hexdigest()}", flush=True)


if __name__ == "__main__":
    main()
