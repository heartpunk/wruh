import Wruh.FreshExtraction

namespace Wruh.AyxgSymex
open Ayxg.QfAbv Wruh.FreshExtraction

variable {Γ : Ctx} [FPInterpretation]

/-- The reference instance uses AYXG's whole-model symbolic stepper directly. -/
def adapter (Γ : Ctx) : Adapter (QFAbvSTS Γ) Unit Unit Γ where
  emulate model := model.toLTS.canStep
  symex model input := (model.symbolicStep input).map fun successor =>
    { site := (), step := successor, metadata := () }

/-- AYXG's existing symbolic-step theorem is exactly the adapter law. -/
theorem laws : SymexLaws (adapter Γ) where
  soundComplete := by
    intro model input ρ target
    have correspondence := QFAbvSTS.symbolicStep_denotes_iff model input ρ target
    constructor
    · rintro ⟨tagged, present, denotes⟩
      obtain ⟨successor, member, rfl⟩ := List.mem_map.1 present
      exact correspondence.1 ⟨successor, member, denotes⟩
    · intro concrete
      obtain ⟨successor, member, denotes⟩ := correspondence.2 concrete
      exact ⟨{ site := (), step := successor, metadata := () },
        List.mem_map.2 ⟨successor, member, rfl⟩, denotes⟩

/-- Recover every AYXG STS through the same generic symex interface. -/
theorem recovers (model : QFAbvSTS Γ) (s t : Env Γ) :
    (extract (adapter Γ) model).toLTS.canStep s t ↔ model.toLTS.canStep s t :=
  extract_transport (adapter Γ) laws model s t

theorem bisimilar (model : QFAbvSTS Γ) :
    IsBisimulation (extract (adapter Γ) model).toLTS.canStep model.toLTS.canStep Eq :=
  extract_bisimulation (adapter Γ) laws model

end Wruh.AyxgSymex
