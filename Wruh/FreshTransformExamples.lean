import Wruh.FreshTransform

namespace Wruh.FreshTransformExamples

open Ayxg.QfAbv Wruh.Observation Wruh.FreshTransform
@[simp] private theorem lookup_head {d : Decl} {Γ : Ctx}
    (value : Denote d.sort) (rest : Env Γ) :
    Env.lookup (Env.cons (d := d) value rest) Var.here = value := rfl

@[simp] private theorem lookup_tail {d : Decl} {Γ : Ctx} {s : TermSort}
    (value : Denote d.sort) (rest : Env Γ) (x : Var Γ s) :
    Env.lookup (Env.cons (d := d) value rest) (Var.there x) =
      Env.lookup rest x := rfl

variable [FPInterpretation]

private def registers : Ctx := [⟨"x", .bv 8⟩, ⟨"y", .bv 8⟩]

private def swap : ResolvedOutcome registers Unit where
  before := StateUpdate.identity registers
  after := .cons (.var (.there .here)) (.cons (.var .here) .nil)
  guard := .boolLit true
  metadata := ()

/-- Assignments are simultaneous: y receives old x, not the new x. -/
example (x y : BitVec 8) :
    (fromResolved (.boolLit true) swap).step.update.eval (.cons x (.cons y .nil)) =
      .cons y (.cons x .nil) := rfl

example (s t : Env registers) :
    (fromResolved (.boolLit true) swap).step.denotes s t ↔
      observedResolved (.boolLit true) swap s t :=
  fromResolved_denotes_iff _ _ (fresh_identity _ _ rfl) s t

/-- Identity retains every state component, including arrays and FP values. -/
example {Γ : Ctx} (s : Env Γ) :
    (fromResolved (.boolLit true)
      ({ before := StateUpdate.identity Γ, after := StateUpdate.identity Γ,
         guard := .boolLit true, metadata := () } : ResolvedOutcome Γ Unit)).step.update.eval s = s :=
  StateUpdate.eval_identity s

private def memoryCtx : Ctx :=
  [⟨"memory", .array 8 8⟩, ⟨"a", .bv 8⟩, ⟨"b", .bv 8⟩]

private def writes : ResolvedOutcome memoryCtx String where
  before := StateUpdate.identity memoryCtx
  after := .cons
    (.store 8 8 (.store 8 8 (.var .here) (.var (.there .here)) (.bvLit 8 17))
      (.var (.there (.there .here))) (.bvLit 8 99))
    (.cons (.var (.there .here)) (.cons (.var (.there (.there .here))) .nil))
  guard := .boolLit true
  metadata := "symbolic-target"

/-- Both aliasing and disjoint writes: the later store wins exactly on alias. -/
example (m : Mem 8 8) (a b : BitVec 8) :
    Env.lookup ((fromResolved (.boolLit true) writes).step.update.eval
      (.cons m (.cons a (.cons b .nil)))) .here a =
        if a = b then BitVec.ofNat 8 99 else BitVec.ofNat 8 17 := by
  change (if a = b then BitVec.ofNat 8 99 else
    if a = a then BitVec.ofNat 8 17 else m a) = _
  simp

/-- Fault/target annotation is retained without interpretation. -/
example {Γ : Ctx} (o : ResolvedOutcome Γ String) (h : o.metadata = "error") :
    (fromResolved (.boolLit true) o).metadata = "error" := h

private def controlCtx : Ctx := [⟨"pc", .bv 8⟩]
private def atSource : Expr controlCtx .bool := .eqBv 8 (.var .here) (.bvLit 8 7)
private def advance : ResolvedOutcome controlCtx Unit where
  before := .cons (.bvLit 8 7) .nil
  after := .cons (.bvLit 8 8) .nil
  guard := .boolLit true
  metadata := ()

/-- Concrete source specialization is identity under its source guard. -/
private theorem advance_fresh : FreshResolved atSource advance := by
  intro input hsource _
  cases input with
  | cons pc rest =>
    cases rest
    change (pc == BitVec.ofNat 8 7) = true at hsource
    have hpc : pc = BitVec.ofNat 8 7 := by simpa using hsource
    subst pc
    rfl

example (s t : Env controlCtx) :
    (fromResolved atSource advance).step.denotes s t ↔ observedResolved atSource advance s t :=
  fromResolved_denotes_iff _ _ advance_fresh s t

/-- A false path condition creates no transition. -/
example {Γ : Ctx} (o : ResolvedOutcome Γ Unit) (s t : Env Γ) :
    ¬ (fromResolved (.boolLit false) o).step.denotes s t := by
  simp [fromResolved, QFAbvStep.denotes, Eval.evalBool, Eval.eval]

/-- Two-byte loads put the first address in the low byte. -/
example {Γ : Ctx} (env : Env Γ) :
    Eval.eval env (ByteMemory.loadLE 1
      (.store 8 8 (.constArray 8 8 (.bvLit 8 187)) (.bvLit 8 0) (.bvLit 8 170))
      (.bvLit 8 0)) = BitVec.ofNat 16 48042 := by
  rw [ByteMemory.eval_loadLE]
  change ByteMemory.loadValue 1
    (fun i => if i = BitVec.ofNat 8 0 then BitVec.ofNat 8 170 else BitVec.ofNat 8 187)
    (BitVec.ofNat 8 0) = _
  decide

/-- Two-byte stores, low byte first; the second address wraps at 8 bits. -/
example (memory : Mem 8 8) :
    ByteMemory.storeValue 1 memory (BitVec.ofNat 8 255) (BitVec.ofNat 16 48042)
      (BitVec.ofNat 8 255) = BitVec.ofNat 8 170 := rfl
example (memory : Mem 8 8) :
    ByteMemory.storeValue 1 memory (BitVec.ofNat 8 255) (BitVec.ofNat 16 48042)
      (BitVec.ofNat 8 0) = BitVec.ofNat 8 187 := rfl
example (memory : Mem 8 8) :
    ByteMemory.storeValue 1 memory (BitVec.ofNat 8 255) (BitVec.ofNat 16 48042)
      (BitVec.ofNat 8 1) = memory (BitVec.ofNat 8 1) := rfl

private def readCtx : Ctx :=
  [⟨"memory", .array 8 8⟩, ⟨"address", .bv 8⟩, ⟨"result", .bv 8⟩]
private def firstCtx : Ctx := ⟨"first", .bv 8⟩ :: readCtx
private def secondCtx : Ctx := ⟨"second", .bv 8⟩ :: firstCtx

/-- First read sees old memory. Second read uses the first read's value as its
address, and sees memory after a write. No substitution is performed in Python. -/
private def reads : LetChain readCtx secondCtx :=
  bindRead
    (bindRead .nil "first" 0 (.var .here) (.var (.there .here)))
    "second" 0
    (ByteMemory.storeLE 0 (.var (.there .here))
      (.var (.there (.there .here))) (.bvLit 8 99))
    (.var .here)

private def dependentReads : Outcome readCtx String where
  temporaryCtx := secondCtx
  bindings := reads
  before := StateUpdate.identity readCtx
  after := .cons
    (ByteMemory.storeLE 0 (.var (.there (.there .here)))
      (.var (.there (.there (.there .here)))) (.bvLit 8 99))
    (.cons (.var (.there (.there (.there .here)))) (.cons (.var .here) .nil))
  guard := .eqBv 8 (.var .here) (.bvLit 8 99)
  metadata := "error"

private theorem dependentReads_fresh : Fresh (.boolLit true) dependentReads := by
  intro input _ _
  exact StateUpdate.eval_identity input

/-- End-to-end local theorem with unresolved ordered reads and a read-dependent guard. -/
example (s t : Env readCtx) :
    (transform (.boolLit true) dependentReads).step.denotes s t ↔
      observed (.boolLit true) dependentReads s t :=
  transform_denotes_iff _ _ dependentReads_fresh s t

/-- Read 1 observes before-write memory; read 2 observes after-write memory.
The result explicitly distinguishes aliasing from nonaliasing. -/
example (m : Mem 8 8) (address result : BitVec 8) :
    Env.lookup ((resolve dependentReads).after.eval
      (.cons m (.cons address (.cons result .nil)))) (.there (.there .here)) =
      if m address = address then BitVec.ofNat 8 99 else m (m address) := by
  dsimp [resolve, dependentReads, reads, bindRead, LetChain.closeUpdate,
    LetChain.close, StateUpdate.eval, Eval.evalBindings, Eval.eval, Env.lookup,
    readCtx, firstCtx, secondCtx, ByteMemory.loadLE, ByteMemory.storeLE,
    ByteMemory.Width, Eval.BvBinOp.apply, List.range, List.foldl]
  simp [Eval.memStore, Eval.memLoad]

example : (transform (.boolLit true) dependentReads).metadata = "error" := rfl

end Wruh.FreshTransformExamples
