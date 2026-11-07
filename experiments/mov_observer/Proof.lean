import Extracted

set_option maxRecDepth 16384
set_option maxHeartbeats 2000000

namespace MovObserver
open Ayxg.QfAbv
variable [FPInterpretation]

/-- A concrete interpretation of the extracted, ordered byte writes. -/
def applyWrites {Δ : Ctx} (s : Env Δ) :
    List (BitVec 64 × Expr Δ (.bv 8)) → Mem 64 8 → Mem 64 8
  | [], m => m
  | w :: ws, m => applyWrites s ws (Eval.memStore m w.1 (Eval.eval s w.2))

theorem eval_storeChain {Δ : Ctx} (s : Env Δ)
    (writes : List (BitVec 64 × Expr Δ (.bv 8)))
    (initial : Expr Δ (.array 64 8)) :
    Eval.eval s (storeChain initial writes) =
      applyWrites s writes (Eval.eval s initial) := by
  induction writes generalizing initial with
  | nil => rfl
  | cons w ws ih =>
    change Eval.eval s (storeChain
      (.store 64 8 initial (.bvLit 64 w.1.toNat) w.2) ws) = _
    rw [ih]
    simp [Eval.eval, applyWrites]

/-- The frame property quantifies over the entire modeled address space. -/
theorem writes_frame {Δ : Ctx} (s : Env Δ)
    (writes : List (BitVec 64 × Expr Δ (.bv 8)))
    (m : Mem 64 8) (a : BitVec 64)
    (outside : ∀ w ∈ writes, a ≠ w.1) :
    applyWrites s writes m a = m a := by
  induction writes generalizing m with
  | nil => rfl
  | cons w ws ih =>
    have rest : ∀ v ∈ ws, a ≠ v.1 := by
      intro v hv
      exact outside v (List.mem_cons_of_mem w hv)
    change applyWrites s ws (Eval.memStore m w.1 (Eval.eval s w.2)) a = m a
    rw [ih _ rest]
    exact if_neg (outside w (List.mem_cons_self))

/-- Unique destinations ensure that subsequent stores preserve each sample. -/
theorem writes_capture {Δ : Ctx} (s : Env Δ)
    (writes : List (BitVec 64 × Expr Δ (.bv 8)))
    (m : Mem 64 8) (w : BitVec 64 × Expr Δ (.bv 8))
    (distinct : (writes.map Prod.fst).Nodup) (member : w ∈ writes) :
    applyWrites s writes m w.1 = Eval.eval s w.2 := by
  induction writes generalizing m with
  | nil => simp at member
  | cons head tail ih =>
    have parts : head.1 ∉ tail.map Prod.fst ∧ (tail.map Prod.fst).Nodup :=
      List.nodup_cons.mp distinct
    rcases List.mem_cons.mp member with same | later
    · subst w
      change applyWrites s tail
        (Eval.memStore m head.1 (Eval.eval s head.2)) head.1 = _
      rw [writes_frame s tail _ head.1]
      · simp [Eval.memStore]
      · intro v hv eq
        apply parts.1
        exact List.mem_map.mpr ⟨v, hv, eq.symm⟩
    · exact ih _ parts.2 later

theorem extracted_destinations_unique :
    (extractedWrites.map Prod.fst).Nodup := by decide

theorem memory_update (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_mem =
      applyWrites s extractedWrites (Env.lookup s v_mem) := by
  change Eval.eval s (storeChain (.var v_mem) extractedWrites) = _
  exact eval_storeChain s extractedWrites (.var v_mem)

/-- The specification is independent of the extracted expression:
each original GPR byte is copied to its designated slot, every other memory
byte is unchanged, and execution advances exactly past the fragment. -/
structure CaptureSpec (s t : Env Γ) : Prop where
  recorded : ∀ w ∈ expectedWrites,
    Env.lookup t v_mem w.1 = Eval.eval s w.2
  framed : ∀ a, (∀ w ∈ expectedWrites, a ≠ w.1) →
    Env.lookup t v_mem a = Env.lookup s v_mem a
  pc : Env.lookup t v_rip = BitVec.ofNat 64 4194416

theorem capture_spec (s : Env Γ) : CaptureSpec s (captureUpdate.eval s) := by
  constructor
  · intro w member
    rw [memory_update]
    apply writes_capture s extractedWrites _ w extracted_destinations_unique
    simpa only [extracted_matches_snapshot_spec] using member
  · intro a outside
    rw [memory_update]
    apply writes_frame
    simpa only [extracted_matches_snapshot_spec] using outside
  · exact final_pc s

theorem modeled_step_captures {s t : Env Γ}
    (step : captureStep.denotes s t) : CaptureSpec s t := by
  have update : captureUpdate.eval s = t := step.2
  rw [← update]
  exact capture_spec s

/-- Explicit conditional hardware transfer. `faithful` is the held-out
semantics/entry/exit contract, not a theorem asserting hardware correctness.
The external supervisor and kernel observation ABI remain calibration
dependencies. This theorem neither assumes nor proves a terminating native
execution for inadmissible states (for example, unmapped record memory). -/
theorem native_capture_if_semantics_correct {NativeState : Type}
    (project : NativeState → Env Γ)
    (nativeStep : NativeState → NativeState → Prop)
    (faithful : ∀ s t, nativeStep s t →
      captureStep.denotes (project s) (project t))
    {s t : NativeState} (step : nativeStep s t) :
    CaptureSpec (project s) (project t) :=
  modeled_step_captures (faithful s t step)

#print axioms extracted_matches_snapshot_spec
#print axioms capture_spec
#print axioms native_capture_if_semantics_correct
end MovObserver
