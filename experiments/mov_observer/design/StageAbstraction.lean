import Protocol

namespace MovObserver.Design
open Ayxg.QfAbv
variable [FPInterpretation]

/-- Availability plus all-result correctness; NOT a divergence-freedom claim. -/
def StageCorrect {I O : Type} (run : I → O → Prop)
    (admissible : I → Prop) (postcond : I → O → Prop) : Prop :=
  ∀ i, admissible i → (∃ o, run i o) ∧ ∀ o, run i o → postcond i o

/-- Data only: no correctness fields or assumed laws. -/
structure FlagsComponents (C E : Type) where
  prepare : Env Γ → Env Γ → Env Γ
  load : QFAbvStep Γ Γ
  capture : QFAbvStep Γ Γ
  decode : Mem 64 8 → Option ModeledFlags
  assemble : C → E → BitVec 64 → Mem 64 8 → Option (FlagsObservation C E)
  classify : Env Γ → FlagsBoundaryResult
  recordBase : Nat
  prepareWrites : List (BitVec 64)
  installWrites : List (BitVec 64)
  captureWrites : List (BitVec 64)
  protectedAddress : BitVec 64 → Prop
  loaderEntry : BitVec 64
  targetEntry : BitVec 64
  captureEntry : BitVec 64
  captureExit : BitVec 64

def admittedInput (i : Env Γ × Env Γ) : Prop :=
  (observeModeledFlags i.1).Valid ∧ (observeModeledFlags i.2).Valid

def PrepareCorrect {C E : Type} (p : FlagsComponents C E) : Prop :=
  StageCorrect (fun i s => s = p.prepare i.1 i.2) admittedInput fun i s =>
    StateFrame flagsInstallChangedFields p.prepareWrites i.2 s ∧
    Env.lookup s v_rip = p.loaderEntry

def LoadCorrect {C E : Type} (p : FlagsComponents C E) : Prop :=
  StageCorrect (fun i s => p.load.denotes (p.prepare i.1 i.2) s)
    admittedInput fun i s =>
      observeModeledFlags s = observeModeledFlags i.1 ∧
      StateFrame flagsInstallChangedFields p.installWrites (p.prepare i.1 i.2) s ∧
      Env.lookup s v_rip = p.targetEntry

def CaptureCorrect {C E : Type} (p : FlagsComponents C E) : Prop :=
  StageCorrect (fun post s => p.capture.denotes (enterCapture post) s)
    (fun post => (observeModeledFlags post).Valid) fun post s =>
      p.decode (Env.lookup s v_mem) = some (observeModeledFlags post) ∧
      StateFrame captureChangedFields p.captureWrites post s ∧
      Env.lookup s v_rip = p.captureExit

/-- Candidate replacement, not adopted into Protocol.lean. -/
def CompactFlagsContract {C E : Type} (p : FlagsComponents C E) : Prop :=
  PrepareCorrect p ∧ LoadCorrect p ∧ CaptureCorrect p ∧
  (∀ post, Env.lookup (enterCapture post) v_rip = p.captureEntry) ∧
  FlagsObservationCorrect p.decode p.assemble ∧
  FlagsConversionCorrect ∧ FlagsArchitecturalLayoutCorrect ∧
  FlagsRecordDecoderCorrect p.recordBase p.decode ∧
  FlagsMemorySeparation p.recordBase p.prepareWrites p.installWrites
    p.captureWrites p.protectedAddress ∧
  FlagsBoundaryClassificationCorrect p.classify

/-- Exact regression obligation for the refactor; not a proof. -/
def PreservesApprovedContract {C E : Type} (p : FlagsComponents C E) : Prop :=
  CompactFlagsContract p ↔
    FlagsProtocolContract p.recordBase p.prepare p.load p.capture p.decode
      p.assemble p.classify p.prepareWrites p.installWrites p.captureWrites
      p.protectedAddress p.loaderEntry p.targetEntry p.captureEntry p.captureExit

/-- Refactor equivalence only; does not discharge either observer contract. -/
theorem preservesApprovedContract {C E : Type} (p : FlagsComponents C E) :
    PreservesApprovedContract p := by
  constructor
  · rintro ⟨hp, hl, hc, he, ho, hcv, ha, hd, hs, hk⟩
    refine ⟨?_, ho, hcv, ha, hd, hs, hk, ?_, ?_⟩
    · refine ⟨?_, ?_, he, ?_⟩
      · intro w a hw hv
        exact ((hp (w,a) ⟨hw,hv⟩).2 _ rfl).2
      · intro w a l hw hv step
        exact ((hl (w,a) ⟨hw,hv⟩).2 l step).2.2
      · intro post captured valid step
        exact ((hc post valid).2 captured step).2.2
    · constructor
      · intro w a hw hv
        exact ⟨(hl (w,a) ⟨hw,hv⟩).1, fun l step => ((hl (w,a) ⟨hw,hv⟩).2 l step).1⟩
      · intro post valid
        exact ⟨(hc post valid).1, fun captured step => ((hc post valid).2 captured step).1⟩
    · refine ⟨?_, ?_, ?_⟩
      · intro w a hw hv
        exact ((hp (w,a) ⟨hw,hv⟩).2 _ rfl).1
      · intro w a l hw hv step
        exact ((hl (w,a) ⟨hw,hv⟩).2 l step).2.1
      · intro post captured valid step
        exact ((hc post valid).2 captured step).2.1
  · rintro ⟨hf, ho, hcv, ha, hd, hs, hk, hi, hr⟩
    refine ⟨?_, ?_, ?_, hf.2.2.1, ho, hcv, ha, hd, hs, hk⟩
    · intro i valid
      refine ⟨⟨p.prepare i.1 i.2, rfl⟩, ?_⟩
      intro s eq
      subst s
      exact ⟨hr.1 i.1 i.2 valid.1 valid.2, hf.1 i.1 i.2 valid.1 valid.2⟩
    · intro i valid
      refine ⟨(hi.1 i.1 i.2 valid.1 valid.2).1, ?_⟩
      intro s step
      exact ⟨(hi.1 i.1 i.2 valid.1 valid.2).2 s step,
        hr.2.1 i.1 i.2 s valid.1 valid.2 step,
        hf.2.1 i.1 i.2 s valid.1 valid.2 step⟩
    · intro post valid
      refine ⟨(hi.2 post valid).1, ?_⟩
      intro captured step
      exact ⟨(hi.2 post valid).2 captured step,
        hr.2.2 post captured valid step, hf.2.2.2 post captured valid step⟩

#print axioms preservesApprovedContract

end MovObserver.Design
