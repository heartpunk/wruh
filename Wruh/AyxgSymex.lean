import Wruh.FreshExtraction

namespace Wruh.AyxgSymex

open Ayxg.QfAbv Ayxg.LTS.QfAbv Wruh.FreshExtraction

variable {Γ : Ctx} [FPInterpretation] {E : Type}

/-- The reference instance uses AYXG's source-indexed symbolic stepper while
keeping each original edge as the label on its returned successor. -/
def adapter (ctx : Ctx) :
    Adapter (SymbolicTransitionSystem Unit ctx E) E ctx where
  reference := id
  symex model input := model.symbolicStep input

/-- AYXG's exact labeled stepping theorem is the adapter law. Both the exact
edge value and complete endpoint configurations are retained. -/
theorem laws : SymexLaws (adapter (E := E) Γ) where
  soundComplete := by
    intro model input source edge target
    cases source with
    | mk sourceControl source =>
      cases sourceControl
      cases target with
      | mk targetControl target =>
        cases targetControl
        exact SymbolicTransitionSystem.symbolicStep_denotes_iff
          model input source edge target

/-- Exact extraction recovery for each source label. The existential is only
over the composed symbolic successor; its `edge` field must equal the source
label. -/
theorem recovers (model : SymbolicTransitionSystem Unit Γ E)
    (source target : Config Unit Γ) (edge : E) :
    (∃ successor,
      (extract (adapter (E := E) Γ) model).toLTS.Tr
        source successor target ∧ successor.edge = edge) ↔
      model.toLTS.Tr source edge target := by
  constructor
  · rintro ⟨successor, transition, sameEdge⟩
    simpa [adapter, sameEdge] using
      extract_transition_sound (adapter (E := E) Γ) laws
        model source target successor transition
  · intro transition
    exact extract_transition_complete (adapter (E := E) Γ)
      laws model source target edge transition

/-- Label-sensitive bisimulation for every source-indexed QF_ABV STS. -/
theorem bisimilar (model : SymbolicTransitionSystem Unit Γ E) :
    IsLabelledBisimulation
      (extract (adapter (E := E) Γ) model).toLTS
      model.toLTS (fun successor edge => successor.edge = edge) Eq :=
  extract_bisimulation (adapter (E := E) Γ) laws model

end Wruh.AyxgSymex
