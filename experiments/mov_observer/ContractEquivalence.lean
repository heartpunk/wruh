import Protocol

namespace MovObserver.Regression
open Ayxg.QfAbv
open Ayxg.LTS.QfAbv (SymbolicTransitionSystem Config)
variable [FPInterpretation]

-- Frozen approved statements from 0985ba2869ed206571f5c4f1fdd179720490affa.
-- Kept only as equivalence-test targets, not the production specification.
def ProtocolFlagsFidelity
    (prepareFlags : Env Γ → Env Γ → Env Γ)
    (flagsLoader flagsCapture : QFAbvStep Γ Γ)
    (decodeFlags : Mem 64 8 → Option ModeledFlags) : Prop :=
  (∀ wanted ambient : Env Γ,
    (observeModeledFlags wanted).Valid →
    (observeModeledFlags ambient).Valid →
    (∃ loaded, flagsLoader.denotes (prepareFlags wanted ambient) loaded) ∧
    (∀ loaded, flagsLoader.denotes (prepareFlags wanted ambient) loaded →
      observeModeledFlags loaded = observeModeledFlags wanted)) ∧
  (∀ post : Env Γ,
    (observeModeledFlags post).Valid →
    (∃ captured, flagsCapture.denotes (enterCapture post) captured) ∧
    (∀ captured, flagsCapture.denotes (enterCapture post) captured →
      decodeFlags (Env.lookup captured v_mem) = some (observeModeledFlags post)))

def FlagsProtocolFrames
    (prepareFlags : Env Γ → Env Γ → Env Γ)
    (flagsLoader flagsCapture : QFAbvStep Γ Γ)
    (prepareWrites installWrites captureWrites : List (BitVec 64)) : Prop :=
  (∀ wanted ambient : Env Γ,
    (observeModeledFlags wanted).Valid →
    (observeModeledFlags ambient).Valid →
    StateFrame flagsInstallChangedFields prepareWrites
      ambient (prepareFlags wanted ambient)) ∧
  (∀ wanted ambient loaded : Env Γ,
    (observeModeledFlags wanted).Valid →
    (observeModeledFlags ambient).Valid →
    flagsLoader.denotes (prepareFlags wanted ambient) loaded →
    StateFrame flagsInstallChangedFields installWrites
      (prepareFlags wanted ambient) loaded) ∧
  (∀ post captured : Env Γ,
    (observeModeledFlags post).Valid →
    flagsCapture.denotes (enterCapture post) captured →
    StateFrame captureChangedFields captureWrites post captured)

def FlagsControlFlowCorrect
    (prepareFlags : Env Γ → Env Γ → Env Γ)
    (flagsLoader flagsCapture : QFAbvStep Γ Γ)
    (loaderEntry targetEntry captureEntry captureExit : BitVec 64) : Prop :=
  (∀ wanted ambient : Env Γ,
    (observeModeledFlags wanted).Valid →
    (observeModeledFlags ambient).Valid →
    Env.lookup (prepareFlags wanted ambient) v_rip = loaderEntry) ∧
  (∀ wanted ambient loaded : Env Γ,
    (observeModeledFlags wanted).Valid →
    (observeModeledFlags ambient).Valid →
    flagsLoader.denotes (prepareFlags wanted ambient) loaded →
    Env.lookup loaded v_rip = targetEntry) ∧
  (∀ post : Env Γ, Env.lookup (enterCapture post) v_rip = captureEntry) ∧
  (∀ post captured : Env Γ,
    (observeModeledFlags post).Valid →
    flagsCapture.denotes (enterCapture post) captured →
    Env.lookup captured v_rip = captureExit)

def ApprovedFlagsProtocolContract {C E : Type} (recordBase : Nat)
    (prepareFlags : Env Γ → Env Γ → Env Γ)
    (flagsLoader flagsCapture : QFAbvStep Γ Γ)
    (decodeFlags : Mem 64 8 → Option ModeledFlags)
    (assemble : C → E → BitVec 64 → Mem 64 8 → Option (FlagsObservation C E))
    (classify : Env Γ → FlagsBoundaryResult)
    (prepareWrites installWrites captureWrites : List (BitVec 64))
    (protectedAddress : BitVec 64 → Prop)
    (loaderEntry targetEntry captureEntry captureExit : BitVec 64) : Prop :=
  FlagsControlFlowCorrect prepareFlags flagsLoader flagsCapture
    loaderEntry targetEntry captureEntry captureExit ∧
  FlagsObservationCorrect decodeFlags assemble ∧
  FlagsConversionCorrect ∧
  FlagsArchitecturalLayoutCorrect ∧
  FlagsRecordDecoderCorrect recordBase decodeFlags ∧
  FlagsMemorySeparation recordBase prepareWrites installWrites captureWrites
    protectedAddress ∧
  FlagsBoundaryClassificationCorrect classify ∧
  ProtocolFlagsFidelity prepareFlags flagsLoader flagsCapture decodeFlags ∧
  FlagsProtocolFrames prepareFlags flagsLoader flagsCapture
    prepareWrites installWrites captureWrites

def ApprovedFlagsModeledEndToEnd {C E : Type}
    (target : SymbolicTransitionSystem C Γ E)
    (recordBase : Nat)
    (prepareFlags : Env Γ → Env Γ → Env Γ)
    (flagsLoader flagsCapture : QFAbvStep Γ Γ)
    (decodeFlags : Mem 64 8 → Option ModeledFlags)
    (assemble : C → E → BitVec 64 → Mem 64 8 → Option (FlagsObservation C E))
    (classify : Env Γ → FlagsBoundaryResult)
    (prepareWrites installWrites captureWrites : List (BitVec 64))
    (protectedAddress : BitVec 64 → Prop)
    (loaderEntry targetEntry captureEntry captureExit : BitVec 64) : Prop :=
  ApprovedFlagsProtocolContract recordBase prepareFlags flagsLoader flagsCapture
    decodeFlags assemble classify prepareWrites installWrites captureWrites
    protectedAddress loaderEntry targetEntry captureEntry captureExit ∧
  ∀ (wanted ambient : Env Γ),
    (observeModeledFlags wanted).Valid →
    (observeModeledFlags ambient).Valid →
    (∃ loaded, flagsLoader.denotes (prepareFlags wanted ambient) loaded) ∧
    (∀ loaded, flagsLoader.denotes (prepareFlags wanted ambient) loaded →
      observeModeledFlags loaded = observeModeledFlags wanted ∧
      Env.lookup loaded v_rip = targetEntry ∧
      StateFrame flagsInstallChangedFields (prepareWrites ++ installWrites)
        ambient loaded ∧
      ∀ (control : C) (edge : E) (post : Config C Γ),
        target.toLTS.Tr ⟨control, loaded⟩ edge post →
        (classify post.env =
          if (observeModeledFlags post.env).Valid then
            FlagsBoundaryResult.valid (observeModeledFlags post.env)
          else
            FlagsBoundaryResult.invalidEncoding (observeModeledFlags post.env)) ∧
        ((observeModeledFlags post.env).Valid →
          (∃ captured, flagsCapture.denotes (enterCapture post.env) captured) ∧
          (∀ captured, flagsCapture.denotes (enterCapture post.env) captured →
            assemble post.control edge (Env.lookup post.env v_rip)
                (Env.lookup captured v_mem) =
              some ⟨post.control, edge, Env.lookup post.env v_rip,
                observeModeledFlags post.env⟩ ∧
            StateFrame captureChangedFields captureWrites post.env captured ∧
            Env.lookup captured v_rip = captureExit)))

/-- Exact regression obligation for the refactor; not a proof. -/
def PreservesApprovedContract {C E : Type} (p : FlagsComponents C E) : Prop :=
  FlagsProtocolContract p ↔
    ApprovedFlagsProtocolContract p.recordBase p.prepare p.load p.capture p.decode
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


/-- The complete flags composition statement is preserved as well. -/
theorem preservesApprovedEndToEnd {C E : Type}
    (target : SymbolicTransitionSystem C Γ E) (p : FlagsComponents C E) :
    FlagsModeledEndToEnd target p ↔
      ApprovedFlagsModeledEndToEnd target p.recordBase p.prepare p.load p.capture
        p.decode p.assemble p.classify p.prepareWrites p.installWrites p.captureWrites
        p.protectedAddress p.loaderEntry p.targetEntry p.captureEntry p.captureExit := by
  unfold FlagsModeledEndToEnd ApprovedFlagsModeledEndToEnd
  exact and_congr (preservesApprovedContract p) Iff.rfl

#print axioms preservesApprovedContract
#print axioms preservesApprovedEndToEnd
end MovObserver.Regression
