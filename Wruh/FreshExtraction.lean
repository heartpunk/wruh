import Wruh.FreshTransform
import Ayxg.QfAbv.SymbolicStep

namespace Wruh.FreshExtraction
open Ayxg.QfAbv Wruh.Observation Wruh.FreshTransform

/-- Primitive operations and independently specified source semantics. -/
structure Adapter (Program Site Metadata : Type) (Γ : Ctx) where
  sites : Program → List Site
  emulate : Program → Env Γ → Env Γ → Prop
  emulateAt : Program → Site → Env Γ → Env Γ → Prop
  input : Program → Site → QFAbvStep Γ Γ
  step : Program → Site → QFAbvStep Γ Γ → List (Outcome Γ Metadata)

variable {P I M : Type} {Γ : Ctx} [FPInterpretation]

/-- Local primitive obligations, independent of the driver and its result. -/
structure SymexLaws (A : Adapter P I M Γ) : Prop where
  sourceCover : ∀ p s t, A.emulate p s t ↔
    ∃ i ∈ A.sites p, Eval.evalBool s (A.input p i).guard = true ∧ A.emulateAt p i s t
  freshInput : ∀ p i, i ∈ A.sites p → ∀ ρ,
    Eval.evalBool ρ (A.input p i).guard = true → (A.input p i).update.eval ρ = ρ
  stepSound : ∀ p i, i ∈ A.sites p → ∀ input outcome,
    outcome ∈ A.step p i input → ∀ ρ,
    Eval.evalBool (outcome.bindings.eval ρ) outcome.guard = true →
      Eval.evalBool ρ input.guard = true ∧
      outcome.before.eval ρ = input.update.eval ρ ∧
      A.emulateAt p i (input.update.eval ρ) (outcome.after.eval (outcome.bindings.eval ρ))
  stepComplete : ∀ p i, i ∈ A.sites p → ∀ input ρ t,
    Eval.evalBool ρ input.guard = true → A.emulateAt p i (input.update.eval ρ) t →
      ∃ outcome ∈ A.step p i input,
        Eval.evalBool (outcome.bindings.eval ρ) outcome.guard = true ∧
        outcome.after.eval (outcome.bindings.eval ρ) = t

/-- Invoke the symbolic engine, then perform the actual ordered-read-aware diff.
The source site and primitive metadata accompany every resulting transformer. -/
def extractTagged (A : Adapter P I M Γ) (p : P) : List (I × Transformer Γ M) :=
  ShareCommon.shareCommon' ((A.sites p).flatMap fun i =>
    let input := A.input p i
    (A.step p i input).map fun outcome => (i, transform input.guard outcome))

/-- Assemble the ordinary AYXG STS; no supplied transcript is an input. -/
def extract (A : Adapter P I M Γ) (p : P) : QFAbvSTS Γ :=
  ⟨(extractTagged A p).map (fun entry => entry.2.step)⟩

private theorem outcome_fresh (A : Adapter P I M Γ) (laws : SymexLaws A)
    (p : P) (i : I) (hi : i ∈ A.sites p) (outcome : Outcome Γ M)
    (ho : outcome ∈ A.step p i (A.input p i)) : Fresh (A.input p i).guard outcome := by
  intro ρ hg hoGuard
  exact ((laws.stepSound p i hi _ outcome ho ρ hoGuard).2.1).trans
    (laws.freshInput p i hi ρ hg)

/-- A helper connects actual engine outcomes to source-site semantics; this
is proved from primitive laws, never supplied as a correctness premise. -/
private theorem outcome_transport (A : Adapter P I M Γ) (laws : SymexLaws A)
    (p : P) (i : I) (hi : i ∈ A.sites p) (s t : Env Γ) :
    (∃ outcome ∈ A.step p i (A.input p i),
      observed (A.input p i).guard outcome s t) ↔
      Eval.evalBool s (A.input p i).guard = true ∧ A.emulateAt p i s t := by
  constructor
  · rintro ⟨outcome, ho, ρ, hbefore, hg, hguard, hafter⟩
    have hinput : ρ = s := (outcome_fresh A laws p i hi outcome ho ρ hg hguard).symm.trans hbefore
    subst ρ
    have step := (laws.stepSound p i hi _ outcome ho s hguard).2.2
    rw [laws.freshInput p i hi s hg, hafter] at step
    exact ⟨hg, step⟩
  · rintro ⟨hg, step⟩
    have hf := laws.freshInput p i hi s hg
    obtain ⟨outcome, ho, hguard, hafter⟩ := laws.stepComplete p i hi (A.input p i) s t hg
      (by simpa only [hf] using step)
    exact ⟨outcome, ho, s, outcome_fresh A laws p i hi outcome ho s hg hguard, hg, hguard, hafter⟩

/-- UNIVERSAL TRANSPORT: the implemented extractor recovers exactly the
adapter's independently specified whole-source transition relation. -/
theorem extract_transport (A : Adapter P I M Γ) (laws : SymexLaws A)
    (p : P) (s t : Env Γ) :
    (extract A p).toLTS.canStep s t ↔ A.emulate p s t := by
  change (∃ step, step ∈ ((extractTagged A p).map (fun e => e.2.step)) ∧ step.denotes s t) ↔ _
  simp only [extractTagged, ShareCommon.shareCommon', List.mem_map, List.mem_flatMap]
  constructor
  · rintro ⟨step, ⟨entry, ⟨i, hi, outcome, ho, he⟩, hs⟩, hd⟩
    subst entry
    subst step
    have observed := (transform_denotes_iff _ outcome (outcome_fresh A laws p i hi outcome ho) s t).1 hd
    exact (laws.sourceCover p s t).2 ⟨i, hi, (outcome_transport A laws p i hi s t).1 ⟨outcome, ho, observed⟩⟩
  · intro source
    obtain ⟨i, hi, hg, step⟩ := (laws.sourceCover p s t).1 source
    obtain ⟨outcome, ho, observed⟩ := (outcome_transport A laws p i hi s t).2 ⟨hg, step⟩
    refine ⟨(transform (A.input p i).guard outcome).step, ?_, ?_⟩
    · exact ⟨(i, transform (A.input p i).guard outcome), ⟨i, hi, outcome, ho, rfl⟩, rfl⟩
    · exact (transform_denotes_iff _ outcome (outcome_fresh A laws p i hi outcome ho) s t).2 observed

/-- Strong bisimulation of complete states for the two unlabeled relations. -/
def IsBisimulation {S : Type} (left right : S → S → Prop) (related : S → S → Prop) : Prop :=
  ∀ s u, related s u →
    (∀ t, left s t → ∃ v, right u v ∧ related t v) ∧
    (∀ v, right u v → ∃ t, left s t ∧ related t v)

theorem extract_bisimulation (A : Adapter P I M Γ) (laws : SymexLaws A) (p : P) :
    IsBisimulation (extract A p).toLTS.canStep (A.emulate p) Eq := by
  intro s u equal
  subst u
  constructor
  · intro t step
    exact ⟨t, (extract_transport A laws p s t).1 step, rfl⟩
  · intro t step
    exact ⟨t, (extract_transport A laws p s t).2 step, rfl⟩

end Wruh.FreshExtraction
