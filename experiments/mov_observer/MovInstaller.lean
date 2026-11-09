import Bootstrap

namespace MovObserver.Bootstrap
open Ayxg.QfAbv
variable [FPInterpretation]

/-- The exact sixteen-MOV loader's input slots, excluded from target memory. -/
def movInputSlots : List (BitVec 64) := inputWrites.map Prod.fst

def movOtherFields : StateView Γ where
  Value := (t : TermSort) → (v : Var Γ t) →
    (⟨t, v⟩ : Σ t, Var Γ t) ∉ inputChangedFields → Denote t
  read s := fun _ v _ => Env.lookup s v

def movOutsideMemory : StateView Γ where
  Value := {a : BitVec 64 // a ∉ movInputSlots} → BitVec 8
  read s := fun a => Env.lookup s v_mem a.val

def movInstallProtected : List (StateView Γ) := [movOtherFields, movOutsideMemory]

/-- Intended installed state: all GPRs, target PC, and every memory byte outside
private input slots. Other modeled fields are preserved, not installed. -/
def movInputState (s : Env Γ) :=
  (observeGprs s, Env.lookup s v_rip, movOutsideMemory.read s)

def movInputQuotient : Setoid (Env Γ) where
  r s t := movInputState s = movInputState t
  iseqv := ⟨fun _ => rfl, Eq.symm, Eq.trans⟩

private theorem prepared_memory (wanted ambient : Env Γ) :
    Env.lookup (prepareInput wanted ambient) v_mem =
      prepareInputMemory wanted (Env.lookup ambient v_mem) := by
  cases ambient with | cons memory tail => cases tail; rfl

private theorem prepared_other (wanted ambient : Env Γ) :
    movOtherFields.read (prepareInput wanted ambient) = movOtherFields.read ambient := by
  funext t v h
  cases v with
  | here => exact False.elim (h (by simp [inputChangedFields, v_mem]))
  | there v =>
    cases v with
    | here => exact False.elim (h (by simp [inputChangedFields, v_mem, v_rip]))
    | there v => cases ambient with | cons memory tail => cases tail; rfl

private theorem outside_prepared (wanted ambient : Env Γ) :
    movOutsideMemory.read (prepareInput wanted ambient) = movOutsideMemory.read ambient := by
  funext a
  change Env.lookup (prepareInput wanted ambient) v_mem a.val = _
  rw [prepared_memory]
  exact writes_frame wanted inputWrites (Env.lookup ambient v_mem) a.val
    (fun w hw heq => a.property (heq ▸ List.mem_map.mpr ⟨w, hw, rfl⟩))

omit [FPInterpretation] in
private theorem frame_meaning (before after : Env Γ) :
    StateFrame inputChangedFields movInputSlots before after ↔
      Preserves movInstallProtected before after := by
  constructor
  · intro h v hv
    simp only [movInstallProtected, List.mem_cons, List.not_mem_nil, or_false] at hv
    rcases hv with rfl | rfl
    · funext t v outside
      exact h.1 t v outside
    · funext a
      exact h.2 a.val a.property
  · intro h
    constructor
    · intro t v outside
      exact congrFun (congrFun (congrFun
        (h movOtherFields (by simp [movInstallProtected])) t) v) outside
    · intro a outside
      exact congrFun (h movOutsideMemory (by simp [movInstallProtected])) ⟨a, outside⟩

/-- Access specification for the already-composed exact loader, not a claim
about all MOV encodings. Reads the input record; changes GPRs and PC only. -/
def movLoaderAccess : AccessSpec Γ where
  enabled s := Eval.evalBool s loadStep.guard = true
  transfers :=
    [⟨⟨List (BitVec 64), observeGprs⟩, fun s => decodeInput (Env.lookup s v_mem)⟩,
     ⟨⟨BitVec 64, fun s => Env.lookup s v_rip⟩, fun _ => BitVec.ofNat 64 0x400170⟩]
  preserved := [movOtherFields, ⟨Mem 64 8, fun s => Env.lookup s v_mem⟩]

/-- Only index zero is used by this installer; no capture access law is claimed. -/
def movInstallerAccess (_ : Fin 2) : AccessSpec Γ := movLoaderAccess

set_option maxHeartbeats 2000000 in
private theorem loader_other (s : Env Γ) :
    movOtherFields.read (loadUpdate.eval s) = movOtherFields.read s := by
  funext t v h
  repeat (first
    | rfl
    | (solve | apply False.elim; apply h; simp [inputChangedFields, v_mem, v_rip, v_rax, v_rcx, v_rdx, v_rbx, v_rsp, v_rbp, v_rsi, v_rdi, v_r8, v_r9, v_r10, v_r11, v_r12, v_r13, v_r14, v_r15])
    | cases ‹Var _ _›)

theorem mov_loader_access_correct : AccessCorrect loadStep movLoaderAccess := by
  intro s enabled
  refine ⟨⟨loadUpdate.eval s, enabled, rfl⟩, ?_⟩
  intro final run
  have eq : loadUpdate.eval s = final := run.2
  rw [← eq]
  constructor
  · intro transfer ht
    simp only [movLoaderAccess, List.mem_cons, List.not_mem_nil, or_false] at ht
    rcases ht with rfl | rfl
    · exact load_input s
    · rfl
  · intro view hv
    simp only [movLoaderAccess, List.mem_cons, List.not_mem_nil, or_false] at hv
    rcases hv with rfl | rfl
    · exact loader_other s
    · exact loader_preserves_mem s

/- The former installer certificate was withdrawn: it assumed requested
memory was already present. The loader access lemma above is not an installer
certificate. Installing requested target memory and reconciling its write frame
with requested PC remain implementation obligations, not request exclusions. -/
#print axioms mov_loader_access_correct
end MovObserver.Bootstrap
