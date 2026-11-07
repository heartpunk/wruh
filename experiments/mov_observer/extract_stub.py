"""Freshly extract the exact observer bytes and emit their AYXG embedding.

The exported model retains every canonical state field. The desired snapshot
specification is constructed independently of the extracted memory expression.
Unexpected guards, writes, state changes, or expression forms stop the export.
No SMT search generates inputs here.
"""
from pathlib import Path
import hashlib
import importlib.metadata
import importlib
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1]))
from extractor import runtime
from extractor import amd64_state as amd
import z3
from stub import CODE, RECORD, GPRS, stub_bytes, write_artifacts


def extract():
    encoded = stub_bytes()
    project = runtime.angr.load_shellcode(encoded, arch="amd64", load_address=CODE)
    block = project.factory.block(CODE, size=len(encoded), num_inst=len(GPRS))
    assert block.size == len(encoded) and block.vex.instructions == len(GPRS)
    decoded = block.capstone.insns
    assert len(decoded) == len(GPRS)
    assert all(i.mnemonic == "mov" and i.size == 7 for i in decoded)
    state = amd.fresh_instruction_state(project, CODE)
    successors = project.factory.successors(state, size=len(encoded),
                                            num_inst=len(GPRS)).all_successors
    assert len(successors) == 1, "capture fragment must have exactly one extracted outcome"
    post = successors[0]
    assert not post.solver.constraints and post.history.jumpkind == "Ijk_Boring"
    post.globals["_wruh_capture_selectors"] = False
    updates = amd._post_updates(post, CODE)
    assert not updates, f"unexpected register/flag writes: {updates}"
    target, value = amd._symbolic_target_update(post, updates)
    assert value == CODE + len(encoded)
    writes = amd._resolved_writes(post)
    assert len(writes) == len(GPRS)
    for index, write in enumerate(writes):
        assert write.size == 8
        assert z3.simplify(write.address).as_long() == RECORD + 8 * index
        assert z3.simplify(write.value).eq(amd.canonical_register(GPRS[index]))
    assert not post.globals["_ghot_memory_reads"], "MOV stores must not read data memory"
    memory = z3.simplify(post.globals["_ghot_memory_expr"])
    byte_writes = []
    base = memory
    while base.decl().kind() == z3.Z3_OP_STORE:
        previous, address, byte = base.children()
        assert z3.is_bv_value(address)
        byte_writes.append((address.as_long(), byte))
        base = previous
    byte_writes.reverse()
    assert base.eq(amd.canonical_memory()) and len(byte_writes) == 8 * len(GPRS)
    assert [a for a, _ in byte_writes] == list(range(RECORD, RECORD + 128))
    return block, memory, byte_writes


def emit_lean(path: Path, writes) -> None:
    declared = {d.name: d for d in amd.canonical_declarations()}
    names = ["mem", "rip", *GPRS]
    names += [name for name in declared if name not in names]
    declarations = [declared[name] for name in names]

    def sort(d):
        return f"(.array {d.index_width} {d.width})" if d.sort == "array" else f"(.bv {d.width})"

    def variable(index):
        return "(" + ".there (" * index + ".here" + ")" * index + ")"

    def expr(e):
        if z3.is_bv_value(e):
            return f"(.bvLit {e.size()} {e.as_long()})"
        if e.decl().kind() == z3.Z3_OP_UNINTERPRETED:
            assert str(e) in names
            return f"(.var v_{e})"
        if e.decl().kind() == z3.Z3_OP_EXTRACT:
            high, low = e.decl().params()
            return (f"(.extract {{ hi := {high}, lo := {low}, hi_lt_width := by decide, "
                    f"lo_le_hi := by decide }} {expr(e.arg(0))})")
        raise ValueError(f"unhandled expression in exact stub: {e.sexpr()}")

    lines = ["-- Generated from the exact observer.bin, not hand-written MOV semantics.",
             f"-- SHA256 {hashlib.sha256(stub_bytes()).hexdigest()}",
             "import Ayxg.QfAbv.Step", "import Ayxg.LTS.QfAbv.SymbolicTransitionSystem",
             "set_option maxRecDepth 16384", "namespace MovObserver", "open Ayxg.QfAbv",
             "def Γ : Ctx := [" + ",\n".join(
                 f'  {{ name := "{d.name}", sort := {sort(d)} }}' for d in declarations) + "]"]
    lines += [f"def v_{d.name} : Var Γ {sort(d)} := {variable(i)}"
              for i, d in enumerate(declarations)]
    lines += ["abbrev ByteWrite := BitVec 64 × Expr Γ (.bv 8)",
              "def extractedWrites : List ByteWrite := [" + ",\n".join(
                  f"  (BitVec.ofNat 64 {address}, {expr(value)})" for address, value in writes) + "]"]
    # Independent contract: slot i contains the original GPRS[i], little endian.
    expected = []
    for i, reg in enumerate(GPRS):
        for b in range(8):
            expected.append(f"  (BitVec.ofNat 64 {RECORD + 8*i + b}, "
                f".extract {{ hi := {8*b+7}, lo := {8*b}, hi_lt_width := by decide, "
                f"lo_le_hi := by decide }} (.var v_{reg}))")
    lines += ["def expectedWrites : List ByteWrite := [" + ",\n".join(expected) + "]",
              "theorem extracted_matches_snapshot_spec : extractedWrites = expectedWrites := rfl",
              "def storeChain {Δ : Ctx} (initial : Expr Δ (.array 64 8))",
              "    (writes : List (BitVec 64 × Expr Δ (.bv 8))) : Expr Δ (.array 64 8) :=",
              "  writes.foldl (fun m w => .store 64 8 m (.bvLit 64 w.1.toNat) w.2) initial",
              "def capturedMemory : Expr Γ (.array 64 8) := storeChain (.var v_mem) extractedWrites"]
    terms = ["capturedMemory", f"(.bvLit 64 {CODE + len(stub_bytes())})"]
    terms += [f"(.var v_{name})" for name in names[2:]]
    update = ".nil"
    for term in reversed(terms):
        update = f"(.cons {term}\n  {update})"
    lines += [f"def captureUpdate : StateUpdate Γ Γ := {update}",
              f"def captureGuard : Expr Γ .bool := .eqBv 64 (.var v_rip) (.bvLit 64 {CODE})",
              "def captureStep : QFAbvStep Γ Γ := ⟨captureGuard, captureUpdate⟩",
              "def model : Ayxg.LTS.QfAbv.SymbolicTransitionSystem Unit Γ Unit where",
              "  edgeSemantics := {",
              "    source := fun _ => ()",
              "    symbolicLabel := fun _ => ⟨captureGuard, captureUpdate⟩",
              "    nextControl := fun _ _ => () }",
              "  transAt := fun _ => [()]",
              "variable [FPInterpretation]"]
    for name in names[2:]:
        lines += [f"theorem preserves_{name} (s : Env Γ) :",
                  f"    Env.lookup (captureUpdate.eval s) v_{name} = Env.lookup s v_{name} := rfl"]
    lines += ["theorem final_pc (s : Env Γ) :",
              f"    Env.lookup (captureUpdate.eval s) v_rip = BitVec.ofNat 64 {CODE+len(stub_bytes())} := rfl",
              "end MovObserver"]
    path.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "out")
    write_artifacts(out)
    block, memory, writes = extract()
    (out / "memory.smt2").write_text(memory.sexpr() + "\n")
    (out / "vex.txt").write_text(str(block.vex) + "\n")
    emit_lean(out / "Extracted.lean", writes)
    def version_info(package):
        try:
            return importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            module_name = {"z3-solver": "z3", "claripy": "angr.claripy"}.get(package, package)
            module = importlib.import_module(module_name)
            origin = getattr(module, "__file__", "bundled extension; see parent distribution")
            return f"{getattr(module, '__version__', 'no version metadata')}; module={module.__name__}; origin={origin}"
    summary = (f"exact_bytes={len(stub_bytes())}; instructions={len(GPRS)}; "
               f"register_updates=rip_only; memory_bytes={len(writes)}\n"
               + str(block.capstone) + "\n"
               + "\n".join(f"{p}={version_info(p)}"
                             for p in ("angr", "pyvex", "claripy", "archinfo", "z3-solver")))
    (out / "extraction.txt").write_text(summary + "\n")
    print(summary, flush=True)
