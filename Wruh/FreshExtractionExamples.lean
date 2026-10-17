import Wruh.AyxgSymex

namespace Wruh.FreshExtractionExamples

open Ayxg Ayxg.QfAbv Ayxg.LTS.QfAbv Wruh.FreshExtraction Wruh.AyxgSymex

variable [FPInterpretation]

private def registers : Ctx := [⟨"x", .bv 8⟩, ⟨"y", .bv 8⟩]

private def swap : QFAbvStep registers registers :=
  ⟨.boolLit true, .cons (.var (.there .here)) (.cons (.var .here) .nil)⟩

private structure NamedEdge (Γ : Ctx) where
  id : Nat
  step : QFAbvStep Γ Γ

private def namedEdgeSemantics {Γ : Ctx} :
    SymbolicEdgeSemantics Unit Γ (NamedEdge Γ) where
  source := fun _ => ()
  symbolicLabel edge := ⟨edge.step.guard, edge.step.update⟩
  nextControl := fun _ _ => ()

private def firstEdge : NamedEdge registers := ⟨17, swap⟩
private def secondEdge : NamedEdge registers := ⟨23, swap⟩

private def model : SymbolicTransitionSystem Unit registers (NamedEdge registers) where
  edgeSemantics := namedEdgeSemantics
  transAt := fun _ => [firstEdge, secondEdge]

/-- The extracted step retains the complete simultaneous update. -/
example (x y : BitVec 8) :
    (((extract (adapter registers) model).transAt ())[0]'(by
      simp [extract, adapter, SymbolicTransitionSystem.ofSymbolicSuccessors]
      rw [SymbolicTransitionSystem.symbolicStep_length]
      simp [model])).step.update.eval
      (.cons x (.cons y .nil)) = .cons y (.cons x .nil) := rfl

/-- These edges have the same guard and update but distinct IDs. Extraction
must retain both exact labels. -/
example (s t : Config Unit registers) :
    model.toLTS.Tr s firstEdge t ∧ model.toLTS.Tr s secondEdge t →
      (∃ first,
        (extract (adapter registers) model).toLTS.Tr s first t ∧
          first.edge = firstEdge) ∧
      (∃ second,
        (extract (adapter registers) model).toLTS.Tr s second t ∧
          second.edge = secondEdge) := by
  rintro ⟨firstTransition, secondTransition⟩
  exact ⟨(recovers model s t firstEdge).2 firstTransition,
    (recovers model s t secondEdge).2 secondTransition⟩

/-- No bounded unrolling is used: even cyclic source rules are matched by the
one-step labeled relation. -/
example : IsLabelledBisimulation
    (extract (adapter registers) model).toLTS model.toLTS
      (fun successor edge => successor.edge = edge) Eq := bisimilar model

end Wruh.FreshExtractionExamples
