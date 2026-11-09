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

/-- This loader fixes PC and only prepares its private slots. Required target
memory must therefore already be present; no arbitrary-memory installer claim. -/
def movInstallerProfile (q : Setoid (Env Γ))
    (recover : List (BitVec 64) → Option (Quotient q)) : Profile Γ q (List (BitVec 64)) :=
  { movProfile q recover with
    admitted := fun wanted ambient =>
      Env.lookup wanted v_rip = BitVec.ofNat 64 0x400170 ∧
      movOutsideMemory.read wanted = movOutsideMemory.read ambient }

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

private theorem mov_installation_coverage (q : Setoid (Env Γ))
    (recover : List (BitVec 64) → Option (Quotient q)) :
    InstallationCoverage (movInstallerProfile q recover) movInputQuotient := by
  intro wanted ambient loaded admitted installed
  have hg := installed.1 ⟨List (BitVec 64), observeGprs⟩ (by simp [movInstallerProfile, movProfile])
  have hp := installed.2 ⟨⟨BitVec 64, fun s => Env.lookup s v_rip⟩,
    fun _ _ => BitVec.ofNat 64 0x400170⟩ (by simp [movInstallerProfile, movProfile])
  have hm := installed.2 ⟨⟨Mem 64 8, fun s => Env.lookup s v_mem⟩,
    fun w a => prepareInputMemory w (Env.lookup a v_mem)⟩
    (by simp [movInstallerProfile, movProfile])
  have mem : movOutsideMemory.read loaded = movOutsideMemory.read wanted := by
    calc
      movOutsideMemory.read loaded = movOutsideMemory.read (prepareInput wanted ambient) := by
        funext a
        change Env.lookup loaded v_mem a.val = Env.lookup (prepareInput wanted ambient) v_mem a.val
        rw [prepared_memory]
        exact congrFun hm a.val
      _ = movOutsideMemory.read ambient := outside_prepared wanted ambient
      _ = movOutsideMemory.read wanted := admitted.2.symm
  change movInputState loaded = movInputState wanted
  exact congrArg₂ Prod.mk hg (congrArg₂ Prod.mk (hp.trans admitted.1.symm) mem)

/-- Concrete installer certificate for the existing sixteen-MOV loader.
No capture completeness or native ABI correspondence is assumed or proved. -/
theorem mov_installer_contract (q : Setoid (Env Γ))
    (recover : List (BitVec 64) → Option (Quotient q)) :
    InstallerContract movInputQuotient (movInstallerProfile q recover)
      movConstruction movInstallerAccess movInstallProtected := by
  refine ⟨mov_installation_coverage q recover, ?_, ?_⟩
  · intro wanted ambient loaded
    exact frame_meaning ambient loaded
  · intro wanted ambient admitted
    change AccessSequence movBasis movInstallerAccess [0]
      (fun s => s = prepareInput wanted ambient) _
    refine ⟨mov_loader_access_correct, ?_, ?_⟩
    · intro s hs
      subst s
      exact (input_enables_loader wanted ambient).1
    · refine ⟨(fun loaded =>
        (∀ v ∈ (movInstallerProfile q recover).inputViews, v.read loaded = v.read wanted) ∧
        (∀ b ∈ (movInstallerProfile q recover).boundaryValues,
          b.destination.read loaded = b.value wanted ambient) ∧
        Preserves movInstallProtected ambient loaded), ?_, ?_⟩
      · intro before after hbefore effect
        subst before
        have hg := effect.1
          ⟨⟨List (BitVec 64), observeGprs⟩, fun s => decodeInput (Env.lookup s v_mem)⟩
          (by simp [movInstallerAccess, movLoaderAccess])
        have hp := effect.1
          ⟨⟨BitVec 64, fun s => Env.lookup s v_rip⟩, fun _ => BitVec.ofNat 64 0x400170⟩
          (by simp [movInstallerAccess, movLoaderAccess])
        have hm := effect.2 ⟨Mem 64 8, fun s => Env.lookup s v_mem⟩
          (by simp [movInstallerAccess, movLoaderAccess])
        have ho := effect.2 movOtherFields (by simp [movInstallerAccess, movLoaderAccess])
        refine ⟨?_, ?_, ?_⟩
        · intro v hv
          simp only [movInstallerProfile, movProfile, List.mem_cons, List.not_mem_nil, or_false] at hv
          subst v
          exact hg.trans ((load_input (prepareInput wanted ambient)).symm.trans
            (input_installed wanted ambient))
        · intro b hb
          simp only [movInstallerProfile, movProfile, List.mem_cons, List.not_mem_nil, or_false] at hb
          rcases hb with rfl | rfl
          · exact hp
          · exact hm.trans (prepared_memory wanted ambient)
        · intro v hv
          simp only [movInstallProtected, List.mem_cons, List.not_mem_nil, or_false] at hv
          rcases hv with rfl | rfl
          · exact ho.trans (prepared_other wanted ambient)
          · calc
              movOutsideMemory.read after = movOutsideMemory.read (prepareInput wanted ambient) := by
                funext a
                exact congrFun hm a.val
              _ = movOutsideMemory.read ambient := outside_prepared wanted ambient
      · intro s hs
        exact hs

#print axioms mov_installer_contract
end MovObserver.Bootstrap
