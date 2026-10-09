import Wruh.AyxgSymex

namespace Wruh.FreshExtractionExamples
open Ayxg.QfAbv Wruh.FreshExtraction Wruh.AyxgSymex
variable [FPInterpretation]

private def registers : Ctx := [⟨"x", .bv 8⟩, ⟨"y", .bv 8⟩]
private def swap : QFAbvStep registers registers :=
  ⟨.boolLit true, .cons (.var (.there .here)) (.cons (.var .here) .nil)⟩
private def model : QFAbvSTS registers := ⟨[swap]⟩

/-- Evaluate the actual extracted update: assignments remain simultaneous. -/
example (x y : BitVec 8) :
    ((extract (adapter registers) model).steps[0]'(by exact Nat.zero_lt_succ 0)).update.eval
      (.cons x (.cons y .nil)) = .cons y (.cons x .nil) := rfl

/-- Empty source remains empty, with no invented transition. -/
example {Γ : Ctx} : (extract (adapter Γ) (⟨[]⟩ : QFAbvSTS Γ)).steps = [] := rfl

/-- Duplicate alternatives survive assembly. -/
example : (extract (adapter registers) (⟨[swap, swap]⟩ : QFAbvSTS registers)).steps.length = 2 := rfl

/-- No bounded unrolling: even a cyclic identity system has exact one-step recovery. -/
example {Γ : Ctx} (s t : Env Γ) :
    (extract (adapter Γ) (⟨[QFAbvStep.identity Γ]⟩ : QFAbvSTS Γ)).toLTS.canStep s t ↔
      (⟨[QFAbvStep.identity Γ]⟩ : QFAbvSTS Γ).toLTS.canStep s t := recovers _ s t

/-- Disabled source edge stays disabled in the actual output. -/
example (s t : Env registers) :
    ¬ (((extract (adapter registers)
      (⟨[⟨.boolLit false, swap.update⟩]⟩ : QFAbvSTS registers)).steps[0]'(by exact Nat.zero_lt_succ 0)).denotes s t) := by
  simp [extract, extractTagged, tagSuccessors, adapter, QFAbvSTS.symbolicStep,
    ShareCommon.shareCommon',
    QFAbvStep.compose, QFAbvStep.identity, QFAbvStep.denotes,
    Eval.evalBool, Eval.eval, Expr.subst]

/-- Arbitrary models, including memory-valued states, require no recovery premise. -/
example {Γ : Ctx} (source : QFAbvSTS Γ) :
    IsBisimulation (extract (adapter Γ) source).toLTS.canStep source.toLTS.canStep Eq :=
  bisimilar source
end Wruh.FreshExtractionExamples
