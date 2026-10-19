import Ayxg.LTS.QfAbv.SymbolicStep

namespace Wruh.FreshExtraction

open Ayxg Ayxg.QfAbv Ayxg.LTS.QfAbv

variable {P E : Type} {Γ : Ctx} [FPInterpretation]

abbrev TaggedSuccessor (Edge : Type) (Γ : Ctx) :=
  SymbolicTransitionSystem.SymbolicSuccessor Edge Γ Γ

/-- A whole-program symbolic executor paired with its independently specified
source-indexed reference STS. The symbolic output keeps the source edge label
and the complete composed QF_ABV step together. -/
structure Adapter (Program Edge : Type) (Γ : Ctx) where
  reference : Program → SymbolicTransitionSystem Unit Γ Edge
  symex : Program → QFAbvStep Γ Γ → List (TaggedSuccessor Edge Γ)

/-- Exact labelled symex law. For each particular label and complete target
configuration, a returned successor with that label denotes exactly the
reference transition. -/
structure SymexLaws (A : Adapter P E Γ) : Prop where
  soundComplete : ∀ (p : P) (input : QFAbvStep Γ Γ)
      (source : Config Unit Γ) (edge : E) (target : Config Unit Γ),
    (∃ successor ∈ A.symex p input,
      successor.edge = edge ∧
        successor.step.denotes source.env target.env) ↔
      Eval.evalBool source.env input.guard = true ∧
        (A.reference p).toLTS.Tr
          ⟨(), input.update.eval source.env⟩ edge target

/-- The extracted system keeps each symbolic successor, including its source
edge label, as the transition label. Its endpoint states are complete AYXG
configurations; the structural control component is `Unit`. -/
def extract (A : Adapter P E Γ) (p : P) :
    SymbolicTransitionSystem Unit Γ (TaggedSuccessor E Γ) :=
  SymbolicTransitionSystem.ofSymbolicSuccessors
    (A.symex p (QFAbvStep.identity Γ))

/-- The extracted LTS transition is exactly membership of the retained
successor and denotation of its complete step. -/
theorem extract_transition_iff (A : Adapter P E Γ) (p : P)
    (source target : Config Unit Γ) (successor : TaggedSuccessor E Γ) :
    (extract A p).toLTS.Tr source successor target ↔
      successor ∈ A.symex p (QFAbvStep.identity Γ) ∧
        successor.step.denotes source.env target.env := by
  cases source with
  | mk sourceControl sourceEnv =>
    cases sourceControl
    cases target with
    | mk targetControl targetEnv =>
      cases targetControl
      simp [extract, SymbolicTransitionSystem.ofSymbolicSuccessors,
        SymbolicTransitionSystem.toLTS, SymbolicEdgeSemantics.denotes,
        SymbolicEdgeSemantics.nextConfig, SymbolicLabel.denotes,
        QFAbvStep.denotes]

/-- Every extracted transition preserves its exact source label in the
reference semantics. -/
theorem extract_transition_sound (A : Adapter P E Γ) (laws : SymexLaws A)
    (p : P) (source target : Config Unit Γ) (successor : TaggedSuccessor E Γ)
    (transition : (extract A p).toLTS.Tr source successor target) :
    (A.reference p).toLTS.Tr source successor.edge target := by
  have extracted := (extract_transition_iff A p source target successor).1 transition
  have law := (laws.soundComplete p (QFAbvStep.identity Γ) source
      successor.edge target).1
    ⟨successor, extracted.1, rfl, extracted.2⟩
  simpa [QFAbvStep.identity, StateUpdate.eval_identity] using law.2

/-- Every reference transition is extracted with the identical edge label and
complete endpoint configurations. -/
theorem extract_transition_complete (A : Adapter P E Γ)
    (laws : SymexLaws A) (p : P) (source target : Config Unit Γ)
    (edge : E) (transition : (A.reference p).toLTS.Tr source edge target) :
    ∃ successor, (extract A p).toLTS.Tr source successor target ∧
      successor.edge = edge := by
  have law := (laws.soundComplete p (QFAbvStep.identity Γ) source edge target).2
    ⟨by simp [QFAbvStep.identity, Eval.evalBool, Eval.eval], by
      simpa [QFAbvStep.identity, StateUpdate.eval_identity] using transition⟩
  rcases law with ⟨successor, member, edgeEq, denotes⟩
  exact ⟨successor,
    (extract_transition_iff A p source target successor).2 ⟨member, denotes⟩,
    edgeEq⟩

/-- Control is observed from the symbolic environment. For an ISA this view
contains the program counter and exception/error state; for another machine it
can expose that machine's own control-relevant state. -/
structure StateControl (ProgramCounter ErrorState : Type) where
  pc : ProgramCounter
  errors : ErrorState

structure ControlView (Γ : Ctx) (ProgramCounter ErrorState : Type) where
  decode : Env Γ → StateControl ProgramCounter ErrorState

/-- Decode the PC and error state from typed fields inside the environment.
Both observations are expressions over `Γ`; neither becomes structural STS
control. -/
def ControlView.ofBvFields {Γ : Ctx} {pcWidth errorWidth : Nat}
    (pc : Expr Γ (.bv pcWidth)) (errors : Expr Γ (.bv errorWidth)) :
    ControlView Γ (BitVec pcWidth) (BitVec errorWidth) where
  decode env := {
    pc := Eval.evalBv env pc
    errors := Eval.evalBv env errors
  }

/-- A fault event retains a source-state predicate as symbolic provenance. -/
structure FaultEvent (Γ : Ctx) (FaultKind : Type) where
  kind : FaultKind
  trigger : Expr Γ .bool

inductive OutcomeKind (Γ : Ctx) (FaultKind : Type) where
  | ordinary
  | fault (event : FaultEvent Γ FaultKind)
  | recovery (event : FaultEvent Γ FaultKind)

/-- The state-facing fields of one retained transition label. Other provenance
can remain in the edge value without being interpreted by this view. -/
structure OutcomeView (Edge : Type) (Γ : Ctx) (ProgramCounter FaultKind : Type) where
  site : Edge → ProgramCounter
  target : Edge → Env Γ → ProgramCounter
  targetValue : Edge → Option ProgramCounter
  kind : Edge → OutcomeKind Γ FaultKind

/-- A label agrees with the complete source/target states: its site is the
source PC, its symbolic and optional concrete targets are the successor PC,
its typed fault/recovery trigger holds at the source, and its kind accounts
for the error-state change. -/
def OutcomeControlAgrees {Edge : Type} {Γ : Ctx}
    {ProgramCounter FaultKind ErrorState : Type}
    (control : ControlView Γ ProgramCounter ErrorState)
    (outcome : OutcomeView Edge Γ ProgramCounter FaultKind)
    (errorAfter : OutcomeKind Γ FaultKind → Env Γ → ErrorState → ErrorState)
    (edge : Edge) (source target : Config Unit Γ) : Prop :=
  outcome.site edge = (control.decode source.env).pc ∧
  outcome.target edge source.env = (control.decode target.env).pc ∧
  (outcome.targetValue edge = none ∨
    ∃ value, outcome.targetValue edge = some value ∧
      outcome.target edge source.env = value) ∧
  (match outcome.kind edge with
    | .ordinary => True
    | .fault event => Eval.evalBool source.env event.trigger = true
    | .recovery event => Eval.evalBool source.env event.trigger = true) ∧
  (control.decode target.env).errors =
    errorAfter (outcome.kind edge) source.env
      (control.decode source.env).errors

/-- The idealized reference driver promises that every labeled transition
respects the control/error interpretation of its retained outcome data. -/
structure OutcomeLaws (A : Adapter P E Γ)
    {ProgramCounter FaultKind ErrorState : Type}
    (control : ControlView Γ ProgramCounter ErrorState)
    (outcome : OutcomeView E Γ ProgramCounter FaultKind)
    (errorAfter : OutcomeKind Γ FaultKind → Env Γ → ErrorState → ErrorState) : Prop where
  referenceAgrees : ∀ p source edge target,
    (A.reference p).toLTS.Tr source edge target →
      OutcomeControlAgrees control outcome errorAfter edge source target

/-- The extraction transports the reference model's explicit PC and error
state contract onto every extracted edge. -/
theorem extract_outcome_agrees (A : Adapter P E Γ) (laws : SymexLaws A)
    {ProgramCounter FaultKind ErrorState : Type}
    (control : ControlView Γ ProgramCounter ErrorState)
    (outcome : OutcomeView E Γ ProgramCounter FaultKind)
    (errorAfter : OutcomeKind Γ FaultKind → Env Γ → ErrorState → ErrorState)
    (outcomes : OutcomeLaws A control outcome errorAfter)
    (p : P) (source target : Config Unit Γ)
    (successor : TaggedSuccessor E Γ)
    (transition : (extract A p).toLTS.Tr source successor target) :
    OutcomeControlAgrees control outcome errorAfter successor.edge source target :=
  outcomes.referenceAgrees p source successor.edge target
    (extract_transition_sound A laws p source target successor transition)

/-- Label-sensitive bisimulation permits different label representations, but
requires an explicit relation between the labels on each matched step. -/
def IsLabelledBisimulation {S LeftLabel RightLabel : Type}
    (left : LTS S LeftLabel) (right : LTS S RightLabel)
    (labelsMatch : LeftLabel → RightLabel → Prop)
    (related : S → S → Prop) : Prop :=
  ∀ s u, related s u →
    (∀ label t, left.Tr s label t →
      ∃ otherLabel v, right.Tr u otherLabel v ∧
        labelsMatch label otherLabel ∧ related t v) ∧
    (∀ otherLabel v, right.Tr u otherLabel v →
      ∃ label t, left.Tr s label t ∧
        labelsMatch label otherLabel ∧ related t v)

/-- The extraction and source semantics are bisimilar on complete states, with
each extracted label matched to its exact original edge label. -/
theorem extract_bisimulation (A : Adapter P E Γ) (laws : SymexLaws A)
    (p : P) :
    IsLabelledBisimulation (extract A p).toLTS (A.reference p).toLTS
      (fun successor edge => successor.edge = edge) Eq := by
  intro source target equal
  subst target
  constructor
  · intro successor next transition
    exact ⟨successor.edge, next,
      extract_transition_sound A laws p source next successor transition,
      rfl, rfl⟩
  · intro edge next transition
    obtain ⟨successor, extracted, edgeEq⟩ :=
      extract_transition_complete A laws p source next edge transition
    exact ⟨successor, next, extracted, edgeEq, rfl⟩

/-- The full labeled result pairs bisimulation with the state interpretation
of each edge's program counter and typed outcome. -/
theorem extract_bisimulation_and_outcomes (A : Adapter P E Γ)
    (laws : SymexLaws A)
    {ProgramCounter FaultKind ErrorState : Type}
    (control : ControlView Γ ProgramCounter ErrorState)
    (outcome : OutcomeView E Γ ProgramCounter FaultKind)
    (errorAfter : OutcomeKind Γ FaultKind → Env Γ → ErrorState → ErrorState)
    (outcomes : OutcomeLaws A control outcome errorAfter) (p : P) :
    IsLabelledBisimulation (extract A p).toLTS (A.reference p).toLTS
      (fun successor edge => successor.edge = edge) Eq ∧
    (∀ source target successor,
      (extract A p).toLTS.Tr source successor target →
        OutcomeControlAgrees control outcome errorAfter
          successor.edge source target) := by
  exact ⟨extract_bisimulation A laws p,
    fun source target successor transition =>
      extract_outcome_agrees A laws control outcome errorAfter outcomes
        p source target successor transition⟩

end Wruh.FreshExtraction
