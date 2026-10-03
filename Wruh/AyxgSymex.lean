import Wruh.FreshExtraction

namespace Wruh.AyxgSymex
open Ayxg.QfAbv Wruh.Observation Wruh.FreshExtraction

/-- AYXG already expresses successors over the input context: no read temporaries. -/
def observation {Γ : Ctx} (input successor : QFAbvStep Γ Γ) : Outcome Γ Unit where
  temporaryCtx := Γ
  bindings := .nil
  before := input.update
  after := successor.update
  guard := successor.guard
  metadata := ()

variable {Γ : Ctx} [FPInterpretation]

/-- Real Lean symex instance: invoke the proved AYXG stepper on each source edge.
Neither emulation relation refers to extraction or to symbolic-step output. -/
def adapter (Γ : Ctx) : Adapter (QFAbvSTS Γ) (QFAbvStep Γ Γ) Unit Γ where
  sites model := model.steps
  emulate model := model.toLTS.canStep
  emulateAt _ edge := edge.denotes
  input _ _ := QFAbvStep.identity Γ
  step _ edge input :=
    ((⟨[edge]⟩ : QFAbvSTS Γ).symbolicStep input).map (observation input)

/-- All primitive obligations discharged for every AYXG STS and symbolic input. -/
theorem laws : SymexLaws (adapter Γ) where
  sourceCover := by
    intro model s t
    change (∃ edge, edge ∈ model.steps ∧ edge.denotes s t) ↔
      ∃ edge ∈ model.steps, Eval.evalBool s (QFAbvStep.identity Γ).guard = true ∧ edge.denotes s t
    simp [QFAbvStep.identity, Eval.evalBool, Eval.eval]
  freshInput := by
    intro model edge member ρ guard
    exact StateUpdate.eval_identity ρ
  stepSound := by
    intro model edge member input outcome present ρ admitted
    obtain ⟨successor, hs, rfl⟩ := List.mem_map.1 present
    have concrete := QFAbvSTS.symbolicStep_sound (⟨[edge]⟩ : QFAbvSTS Γ) input successor hs ρ admitted
    obtain ⟨hinput, chosen, hc, hd⟩ := concrete
    have he : chosen = edge := List.mem_singleton.1 hc
    subst chosen
    exact ⟨hinput, rfl, hd⟩
  stepComplete := by
    intro model edge member input ρ t admitted concrete
    have singleton : (⟨[edge]⟩ : QFAbvSTS Γ).toLTS.canStep (input.update.eval ρ) t :=
      ⟨edge, List.mem_singleton_self edge, concrete⟩
    obtain ⟨successor, hs, hg, ht⟩ :=
      QFAbvSTS.symbolicStep_complete (⟨[edge]⟩ : QFAbvSTS Γ) input ρ t admitted singleton
    exact ⟨observation input successor, List.mem_map.2 ⟨successor, hs, rfl⟩, hg, ht⟩

/-- No remaining adapter-law premise: recover every supported source AYXG STS. -/
theorem recovers (model : QFAbvSTS Γ) (s t : Env Γ) :
    (extract (adapter Γ) model).toLTS.canStep s t ↔ model.toLTS.canStep s t :=
  extract_transport (adapter Γ) laws model s t

/-- Strong identity bisimulation for arbitrary source models and complete states. -/
theorem bisimilar (model : QFAbvSTS Γ) :
    IsBisimulation (extract (adapter Γ) model).toLTS.canStep model.toLTS.canStep Eq :=
  extract_bisimulation (adapter Γ) laws model

end Wruh.AyxgSymex
