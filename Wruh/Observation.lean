import Ayxg.QfAbv.LetChain

/-! Typed symbolic before/after observations; no execution protocol or driver. -/
namespace Wruh.Observation

open Ayxg.QfAbv

/-- One guarded successor. Both state vectors and the guard are expressions
in the same canonical input context. Before-states may differ between selector
specializations. Metadata retains the primitive's target/fault information. -/
structure ResolvedOutcome (Γ : Ctx) (Metadata : Type) where
  before : StateUpdate Γ Γ
  after : StateUpdate Γ Γ
  guard : Expr Γ .bool
  metadata : Metadata

/-- A primitive observation before temporary-read elimination. Bindings retain
read-time memory expressions and may refer to earlier read results. Canonical
input-state initialization does not require the later temporary context. -/
structure Outcome (Γ : Ctx) (Metadata : Type) where
  temporaryCtx : Ctx
  bindings : LetChain Γ temporaryCtx
  before : StateUpdate Γ Γ
  after : StateUpdate temporaryCtx Γ
  guard : Expr temporaryCtx .bool
  metadata : Metadata

end Wruh.Observation
