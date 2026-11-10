import Bootstrap

namespace MovObserver.Bootstrap
open Ayxg.QfAbv
variable [FPInterpretation]

/-- The exact committed sixteen-MOV capture's byte footprint. -/
def movCaptureSlots : List (BitVec 64) := expectedWrites.map Prod.fst

/-- Every modeled field except capture memory and the fragment PC. -/
def movCaptureOtherFields : StateView Γ where
  Value := (t : TermSort) → (v : Var Γ t) →
    (⟨t, v⟩ : Σ t, Var Γ t) ∉ captureChangedFields → Denote t
  read s := fun _ v _ => Env.lookup s v

/-- All modeled memory outside the concrete capture record, not merely operand memory. -/
def movCaptureOutsideMemory : StateView Γ where
  Value := {a : BitVec 64 // a ∉ movCaptureSlots} → BitVec 8
  read s := fun a => Env.lookup s v_mem a.val

def movCaptureProtected : List (StateView Γ) :=
  [movCaptureOtherFields, movCaptureOutsideMemory]

omit [FPInterpretation] in
theorem mov_capture_frame_meaning (before after : Env Γ) :
    StateFrame captureChangedFields movCaptureSlots before after ↔
      Preserves movCaptureProtected before after := by
  constructor
  · intro h view hv
    simp only [movCaptureProtected, List.mem_cons, List.not_mem_nil, or_false] at hv
    rcases hv with rfl | rfl
    · funext t v outside
      exact h.1 t v outside
    · funext a
      exact h.2 a.val a.property
  · intro h
    constructor
    · intro t v outside
      exact congrFun (congrFun (congrFun
        (h movCaptureOtherFields (by simp [movCaptureProtected])) t) v) outside
    · intro a outside
      exact congrFun (h movCaptureOutsideMemory (by simp [movCaptureProtected])) ⟨a,outside⟩

set_option maxHeartbeats 2000000 in
private theorem capture_other (s : Env Γ) :
    movCaptureOtherFields.read (captureUpdate.eval s) = movCaptureOtherFields.read s := by
  funext t v h
  repeat (first
    | rfl
    | (solve | apply False.elim; apply h; simp [captureChangedFields, v_mem, v_rip])
    | cases ‹Var _ _›)

/-- Exact extracted capture: only its record bytes and PC may change. -/
theorem mov_capture_frame (s : Env Γ) :
    StateFrame captureChangedFields movCaptureSlots s (captureUpdate.eval s) := by
  constructor
  · intro t v outside
    exact congrFun (congrFun (congrFun (capture_other s) t) v) outside
  · intro a outside
    exact (capture_spec s).framed a (fun w hw eq =>
      outside (List.mem_map.mpr ⟨w,hw,eq.symm⟩))

private theorem handoff_other (s : Env Γ) :
    movCaptureOtherFields.read (enterCapture s) = movCaptureOtherFields.read s := by
  funext t v h
  cases v with
  | here => exact False.elim (h (by simp [captureChangedFields, v_mem]))
  | there v =>
    cases v with
    | here => exact False.elim (h (by simp [captureChangedFields, v_mem, v_rip]))
    | there v => cases s with | cons memory tail => cases tail; rfl

private theorem handoff_protected (s : Env Γ) :
    Preserves movCaptureProtected s (enterCapture s) := by
  intro view hv
  simp only [movCaptureProtected, List.mem_cons, List.not_mem_nil, or_false] at hv
  rcases hv with rfl | rfl
  · exact handoff_other s
  · funext a
    exact congrFun (handoff_preserves_memory s) a.val

/-- Discharges the existing endpoint-frame obligation, without a target-semantics
premise or an assumption that the capture preserved the frame. -/
theorem protocol_capture_handoff_frame : ProtocolCaptureHandoffFrame := by
  intro post captured run
  rw [← run.2]
  apply (mov_capture_frame_meaning _ _).mpr
  intro view hv
  exact ((mov_capture_frame_meaning _ _).mp (mov_capture_frame (enterCapture post)) view hv).trans
    (handoff_protected post view hv)

/-- This access is the exact already-composed MOV fragment, not a generic MOV
iform. The transfer receives original GPR values; preservation covers all other
modeled fields and every modeled address outside the capture record. -/
def movCaptureAccess : AccessSpec Γ where
  enabled s := Eval.evalBool s captureStep.guard = true
  transfers :=
    [⟨⟨List (BitVec 64), fun s => decodeRecord (Env.lookup s v_mem)⟩, observeGprs⟩,
     ⟨⟨BitVec 64, fun s => Env.lookup s v_rip⟩, fun _ => BitVec.ofNat 64 0x400070⟩]
  preserved := movCaptureProtected

/-- Only index one is used by the capture sequence; this does not certify a loader. -/
def movCapturerAccess (_ : Fin 2) : AccessSpec Γ := movCaptureAccess

theorem mov_capture_access_correct : AccessCorrect captureStep movCaptureAccess := by
  intro s enabled
  refine ⟨⟨captureUpdate.eval s,enabled,rfl⟩,?_⟩
  intro final run
  rw [← run.2]
  constructor
  · intro transfer ht
    simp only [movCaptureAccess, List.mem_cons, List.not_mem_nil, or_false] at ht
    rcases ht with rfl | rfl
    · exact decode_capture s
    · exact final_pc s
  · exact (mov_capture_frame_meaning _ _).mp (mov_capture_frame s)

/-- Concrete capture-sequence certificate for every original post-state.
No restricted admission predicate or weaker quotient is introduced. The result
is GPR record fidelity plus the full modeled frame; it is not a claim that the
GPR-only record recovers FP/vector/memory state or that ptrace implements handoff. -/
theorem mov_capture_sequence (post : Env Γ) :
    AccessSequence movBasis movCapturerAccess movConstruction.capture
      (fun s => s = enterCapture post)
      (fun final =>
        decodeRecord (Env.lookup final v_mem) = observeGprs post ∧
        Env.lookup final v_rip = BitVec.ofNat 64 0x400070 ∧
        Preserves movCaptureProtected post final) := by
  refine ⟨mov_capture_access_correct,?_,?_⟩
  · intro s hs
    subst s
    exact (handoff_enables_capture post).1
  · refine ⟨fun final => AccessEffect movCaptureAccess (enterCapture post) final,?_,?_⟩
    · intro before after hb effect
      subst before
      exact effect
    · intro final effect
      refine ⟨?_,?_,?_⟩
      · have h := effect.1
          ⟨⟨List (BitVec 64), fun s => decodeRecord (Env.lookup s v_mem)⟩,observeGprs⟩
          (by simp [movCaptureAccess])
        exact h.trans (handoff_preserves_gprs post)
      · exact effect.1
          ⟨⟨BitVec 64, fun s => Env.lookup s v_rip⟩,fun _ => BitVec.ofNat 64 0x400070⟩
          (by simp [movCaptureAccess])
      · intro view hv
        exact (effect.2 view hv).trans (handoff_protected post view hv)

#print axioms protocol_capture_handoff_frame
#print axioms mov_capture_access_correct
#print axioms mov_capture_sequence
end MovObserver.Bootstrap
