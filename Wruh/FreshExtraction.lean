import Wruh.FreshTransform
import Ayxg.QfAbv.SymbolicStep

namespace Wruh.FreshExtraction
open Ayxg.QfAbv Wruh.FreshTransform

/-- A symbolic successor with extraction provenance. -/
structure TaggedSuccessor (Site Metadata : Type) (Γ : Ctx) where
  site : Site
  step : QFAbvStep Γ Γ
  metadata : Metadata

/-- A whole-program symbolic executor and independently specified source semantics. -/
structure Adapter (Program Site Metadata : Type) (Γ : Ctx) where
  emulate : Program → Env Γ → Env Γ → Prop
  symex : Program → QFAbvStep Γ Γ → List (TaggedSuccessor Site Metadata Γ)

variable {P I M : Type} {Γ : Ctx} [FPInterpretation]

/-- The symbolic executor represents exactly the concrete successors of every
admitted symbolic input, as in AYXG's `symbolicStep_denotes_iff`. -/
structure SymexLaws (A : Adapter P I M Γ) : Prop where
  soundComplete : ∀ p input ρ target,
    (∃ successor ∈ A.symex p input, successor.step.denotes ρ target) ↔
      Eval.evalBool ρ input.guard = true ∧
        A.emulate p (input.update.eval ρ) target

/-- Run an operational symex interface from identity, retaining provenance. -/
def extractTaggedWith
    (symex : P → QFAbvStep Γ Γ → List (TaggedSuccessor I M Γ))
    (p : P) : List (I × Transformer Γ M) :=
  (symex p (QFAbvStep.identity Γ)).map fun successor =>
    (successor.site, ⟨successor.step, successor.metadata⟩)

def extractTagged (A : Adapter P I M Γ) (p : P) : List (I × Transformer Γ M) :=
  extractTaggedWith A.symex p

/-- Assemble the ordinary AYXG STS from those same successors. -/
def extract (A : Adapter P I M Γ) (p : P) : QFAbvSTS Γ :=
  ⟨(extractTagged A p).map (fun entry => entry.2.step)⟩

private theorem tagged_steps (A : Adapter P I M Γ) (p : P) :
    (extractTagged A p).map (fun entry => entry.2.step) =
      (A.symex p (QFAbvStep.identity Γ)).map TaggedSuccessor.step := by
  simp [extractTagged, extractTaggedWith, List.map_map]

/-- The actual extraction recovers the whole independently specified relation. -/
theorem extract_transport (A : Adapter P I M Γ) (laws : SymexLaws A)
    (p : P) (s t : Env Γ) :
    (extract A p).toLTS.canStep s t ↔ A.emulate p s t := by
  change (∃ step, step ∈ (extractTagged A p).map (fun entry => entry.2.step) ∧
    step.denotes s t) ↔ _
  rw [tagged_steps A p]
  constructor
  · rintro ⟨step, member, denotes⟩
    obtain ⟨successor, present, rfl⟩ := List.mem_map.1 member
    have concrete := (laws.soundComplete p (QFAbvStep.identity Γ) s t).1
      ⟨successor, present, denotes⟩
    simpa [QFAbvStep.identity, StateUpdate.eval_identity] using concrete.2
  · intro concrete
    have admitted : Eval.evalBool s (QFAbvStep.identity Γ).guard = true ∧
        A.emulate p ((QFAbvStep.identity Γ).update.eval s) t := by
      simp [QFAbvStep.identity, Eval.evalBool, Eval.eval,
        StateUpdate.eval_identity, concrete]
    obtain ⟨successor, present, denotes⟩ :=
      (laws.soundComplete p (QFAbvStep.identity Γ) s t).2 admitted
    exact ⟨successor.step, List.mem_map.2 ⟨successor, present, rfl⟩, denotes⟩

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
