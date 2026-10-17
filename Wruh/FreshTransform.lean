import Wruh.Observation
import Ayxg.QfAbv.Step
import Ayxg.QfAbv.ByteMemory

namespace Wruh.FreshTransform

open Ayxg.QfAbv Wruh.Observation

/-- A guarded transformer and the primitive's unchanged outcome metadata. -/
structure Transformer (Γ : Ctx) (Metadata : Type) where
  step : QFAbvStep Γ Γ
  metadata : Metadata

/-- Dense diff: retain the complete post substitution. Existing expressions and
shared subexpressions are not traversed, duplicated or normalized. -/
def fromResolved {Γ : Ctx} {Metadata : Type}
    (sourceGuard : Expr Γ .bool) (outcome : ResolvedOutcome Γ Metadata) :
    Transformer Γ Metadata where
  step := ⟨.boolAnd sourceGuard outcome.guard, outcome.after⟩
  metadata := outcome.metadata

variable [FPInterpretation]

/-- Meaning of the supplied symbolic before/after pair, independently of
`fromResolved`. All expressions are evaluated in one canonical input valuation. -/
def observedResolved {Γ : Ctx} {Metadata : Type}
    (sourceGuard : Expr Γ .bool) (outcome : ResolvedOutcome Γ Metadata)
    (source target : Env Γ) : Prop :=
  ∃ input, outcome.before.eval input = source ∧
    Eval.evalBool input sourceGuard = true ∧
    Eval.evalBool input outcome.guard = true ∧
    outcome.after.eval input = target

/-- Fresh initialization may specialize control/selectors, provided its guards imply
that the seeded before-state equals the canonical input. This is an explicit
primitive-initialization premise, not a premise about transformer correctness. -/
def FreshResolved {Γ : Ctx} {Metadata : Type}
    (sourceGuard : Expr Γ .bool) (outcome : ResolvedOutcome Γ Metadata) : Prop :=
  ∀ input, Eval.evalBool input sourceGuard = true →
    Eval.evalBool input outcome.guard = true → outcome.before.eval input = input

/-- Exact local transport: both directions, under guarded fresh initialization. -/
theorem fromResolved_denotes_iff {Γ : Ctx} {Metadata : Type}
    (sourceGuard : Expr Γ .bool) (outcome : ResolvedOutcome Γ Metadata)
    (fresh : FreshResolved sourceGuard outcome) (source target : Env Γ) :
    (fromResolved sourceGuard outcome).step.denotes source target ↔
      observedResolved sourceGuard outcome source target := by
  change ((Eval.evalBool source sourceGuard && Eval.evalBool source outcome.guard) = true ∧
    outcome.after.eval source = target) ↔ _
  rw [Bool.and_eq_true]
  constructor
  · rintro ⟨⟨hsource, hguard⟩, hafter⟩
    exact ⟨source, fresh source hsource hguard, hsource, hguard, hafter⟩
  · rintro ⟨input, hbefore, hsource, hguard, hafter⟩
    have hinput : input = source := (fresh input hsource hguard).symm.trans hbefore
    subst input
    exact ⟨⟨hsource, hguard⟩, hafter⟩

/-- A canonical identity before-state satisfies the premise for every guard. -/
theorem fresh_identity {Γ : Ctx} {Metadata : Type}
    (sourceGuard : Expr Γ .bool) (outcome : ResolvedOutcome Γ Metadata)
    (hbefore : outcome.before = StateUpdate.identity Γ) : FreshResolved sourceGuard outcome := by
  intro input _ _
  rw [hbefore, StateUpdate.eval_identity]

/-- No terminal/fault/target metadata is rewritten or discarded. -/
theorem metadata_preserved {Γ : Ctx} {Metadata : Type}
    (sourceGuard : Expr Γ .bool) (outcome : ResolvedOutcome Γ Metadata) :
    (fromResolved sourceGuard outcome).metadata = outcome.metadata := rfl

/-- The exact complete update is retained, including memory and control. -/
theorem update_preserved {Γ : Ctx} {Metadata : Type}
    (sourceGuard : Expr Γ .bool) (outcome : ResolvedOutcome Γ Metadata) :
    (fromResolved sourceGuard outcome).step.update = outcome.after := rfl

/-- Record one positive-width read using its memory snapshot at read time.
This constructor replaces Python's `load_le` portion of read replacement. -/
def bindRead {Γ Δ : Ctx} {iw : Nat} (prior : LetChain Γ Δ)
    (name : String) (extra : Nat) (memory : Expr Δ (.array iw 8))
    (address : Expr Δ (.bv iw)) :
    LetChain Γ ({ name := name, sort := .bv (ByteMemory.Width extra) } :: Δ) :=
  .snoc prior (.cons name (.bv (ByteMemory.Width extra))
    (ByteMemory.loadLE extra memory address) .nil)

/-- Eliminate temporary variables by closure, not expression expansion. -/
def resolve {Γ : Ctx} {Metadata : Type} (outcome : Outcome Γ Metadata) :
    ResolvedOutcome Γ Metadata where
  before := outcome.before
  after := outcome.bindings.closeUpdate outcome.after
  guard := outcome.bindings.close outcome.guard
  metadata := outcome.metadata

/-- Full local construction from a primitive observation with read bindings. -/
def transform {Γ : Ctx} {Metadata : Type}
    (sourceGuard : Expr Γ .bool) (outcome : Outcome Γ Metadata) : Transformer Γ Metadata :=
  fromResolved sourceGuard (resolve outcome)

/-- Supplied observation semantics evaluates read bindings in their original
order before interpreting the primitive's guard and post-state. -/
def observed {Γ : Ctx} {Metadata : Type}
    (sourceGuard : Expr Γ .bool) (outcome : Outcome Γ Metadata)
    (source target : Env Γ) : Prop :=
  ∃ input, outcome.before.eval input = source ∧
    Eval.evalBool input sourceGuard = true ∧
    Eval.evalBool (outcome.bindings.eval input) outcome.guard = true ∧
    outcome.after.eval (outcome.bindings.eval input) = target

/-- Guarded canonical initialization, with temporaries interpreted as supplied. -/
def Fresh {Γ : Ctx} {Metadata : Type}
    (sourceGuard : Expr Γ .bool) (outcome : Outcome Γ Metadata) : Prop :=
  ∀ input, Eval.evalBool input sourceGuard = true →
    Eval.evalBool (outcome.bindings.eval input) outcome.guard = true →
    outcome.before.eval input = input

/-- Closing the bindings preserves precisely their environment semantics. -/
theorem resolve_observed_iff {Γ : Ctx} {Metadata : Type}
    (sourceGuard : Expr Γ .bool) (outcome : Outcome Γ Metadata) (s t : Env Γ) :
    observedResolved sourceGuard (resolve outcome) s t ↔ observed sourceGuard outcome s t := by
  simp only [observedResolved, observed, resolve, Eval.evalBool,
    LetChain.eval_close, LetChain.eval_closeUpdate]

/-- Full local transport, including ordered temporary-read resolution. -/
theorem transform_denotes_iff {Γ : Ctx} {Metadata : Type}
    (sourceGuard : Expr Γ .bool) (outcome : Outcome Γ Metadata)
    (fresh : Fresh sourceGuard outcome) (source target : Env Γ) :
    (transform sourceGuard outcome).step.denotes source target ↔
      observed sourceGuard outcome source target := by
  have closedFresh : FreshResolved sourceGuard (resolve outcome) := by
    intro input hsource hguard
    apply fresh input hsource
    simpa only [resolve, Eval.evalBool, LetChain.eval_close] using hguard
  exact (fromResolved_denotes_iff sourceGuard (resolve outcome) closedFresh source target).trans
    (resolve_observed_iff sourceGuard outcome source target)

/-- Fault, target and provenance metadata survives the entire local pipeline. -/
theorem transform_metadata_preserved {Γ : Ctx} {Metadata : Type}
    (sourceGuard : Expr Γ .bool) (outcome : Outcome Γ Metadata) :
    (transform sourceGuard outcome).metadata = outcome.metadata := rfl

end Wruh.FreshTransform
