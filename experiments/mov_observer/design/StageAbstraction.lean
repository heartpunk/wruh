import Protocol

namespace MovObserver.Design
open Ayxg.QfAbv
variable [FPInterpretation]

/-- Availability plus all-result correctness; NOT a divergence-freedom claim. -/
def StageCorrect {I O : Type} (run : I → O → Prop)
    (admissible : I → Prop) (ensures : I → O → Prop) : Prop :=
  ∀ i, admissible i → (∃ o, run i o) ∧ ∀ o, run i o → ensures i o

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

end MovObserver.Design
