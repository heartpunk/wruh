/-
Planning-only specification. This file defines a goal schema and proves that
the listed component obligations suffice. It implements no observer or bridge.

Concrete instantiation must bind every execution judgment to the named executable
entry point/artifact. In particular, Lean execution retains the concrete foreign
operations; it must not assume they implement the abstract transport. That is
the separate project-owned `abiToProtocol` proof obligation.
-/
import Init

namespace ObserverEndToEndGoal

structure Domain where
  World : Type
  Request : Type
  MachineState : Type
  Event : Type
  Observation : Type
  Failure : Type
  Trace : Type
  CoverageClass : Type
  Prediction : Type

structure TargetOutcome (D : Domain) where
  before : D.MachineState
  after : D.MachineState
  event : D.Event

inductive Result (D : Domain) where
  | observed : D.Observation → Result D
  | failed : D.Failure → Result D

/-- All judgments retain the same complete concrete trace and returned result.
Each judgment may internally relate that trace to its own abstract states.
No prediction is an input to the observation pipeline. -/
abbrev Judgment (D : Domain) :=
  D.World → D.Request → D.Trace → Result D → Prop

/-- Freeze these predicates independently of the implementation. `available`
describes environmental/resource premises, never the computed verdict or assumed
success/safety of project-owned calls. Valid arguments and failure handling must
follow from component proofs. -/
structure Contract (D : Domain) where
  external : D.World → Prop
  admitted : D.Request → Prop
  targetTerminates : D.World → D.Request → Prop
  available : D.World → D.Request → Prop
  requiredClass : D.CoverageClass → Prop
  classOf : D.Request → D.CoverageClass
  requested : D.Request → D.MachineState → Prop
  targetInvocations : D.Trace → Nat
  targetIn : D.Trace → TargetOutcome D → Prop
  represents : TargetOutcome D → D.Observation → Prop
  successFrame : D.Trace → Prop
  failureCorrect : D.Request → D.Trace → D.Failure → Prop
  failureFrame : D.Trace → Prop
  compare : D.Prediction → D.Observation → Bool
  requiredComparison : D.Prediction → TargetOutcome D → Prop

/-- Closed, artifact-bound execution definitions are required at instantiation.
These fields are declaration slots, not correctness assumptions. `Terminates`
means EVERY maximal execution is finite and returns a classified Result: no
infinite run, stuck path or unhandled abort may disappear from the binding.
Divergence is not a permitted Result or a failure alternative. -/
structure Executions (D : Domain) where
  native : Judgment D
  lean : Judgment D
  abi : Judgment D
  protocol : Judgment D
  harness : Judgment D
  nativeTerminates : D.World → D.Request → Prop
  leanTerminates : D.World → D.Request → Prop

def Refines {D : Domain} (C : Contract D)
    (lower upper : Judgment D) : Prop :=
  ∀ w q trace result,
    C.external w → C.admitted q →
    lower w q trace result → upper w q trace result

def OutcomeCorrect {D : Domain} (C : Contract D)
    (q : D.Request) (trace : D.Trace) : Result D → Prop
  | .observed observation =>
      C.targetInvocations trace = 1 ∧
      ∃ outcome, C.targetIn trace outcome ∧
        C.requested q outcome.before ∧ C.represents outcome observation ∧
        C.successFrame trace
  | .failed failure =>
      C.targetInvocations trace ≤ 1 ∧
      C.failureCorrect q trace failure ∧ C.failureFrame trace

def Safe {D : Domain} (C : Contract D) (exec : Judgment D) : Prop :=
  ∀ w q trace result,
    C.external w → C.admitted q → exec w q trace result →
    OutcomeCorrect C q trace result

/-- Required no-divergence obligation. Given a terminating target instruction
and the agreed external/stub semantics, our whole execution must terminate.
This does NOT depend on successful-capture availability. Existence excludes an
empty execution relation satisfying universal termination vacuously. -/
def NoDivergence {D : Domain} (C : Contract D) (exec : Judgment D)
    (terminates : D.World → D.Request → Prop) : Prop :=
  ∀ w q, C.external w → C.admitted q → C.targetTerminates w q →
    terminates w q ∧ ∃ trace result, exec w q trace result

/-- Successful observations under additional environmental/resource premises.
Outside those premises a classified finite failure may occur, but NoDivergence
still applies. A timeout/incomplete label is not a termination proof. -/
def Available {D : Domain} (C : Contract D) (exec : Judgment D) : Prop :=
  ∀ w q, C.external w → C.admitted q → C.targetTerminates w q →
    C.available w q →
    (∃ trace observation, exec w q trace (.observed observation)) ∧
    (∀ trace result, exec w q trace result →
      ∃ observation, result = .observed observation)

/-- Required coverage and external/availability premises must be inhabited.
This is stronger than a theorem whose admission predicate can be always false. -/
def Covered {D : Domain} (C : Contract D) : Prop :=
  (∃ c, C.requiredClass c) ∧
  (∀ c, C.requiredClass c →
    ∃ w q, C.external w ∧ C.admitted q ∧ C.targetTerminates w q ∧
      C.available w q ∧ C.classOf q = c)

/-- The model prediction appears only here, after capture. Agreement with it is
the tested conclusion, never an assumption about the target execution. -/
def ComparisonCorrect {D : Domain} (C : Contract D) : Prop :=
  ∀ prediction outcome observation,
    C.represents outcome observation →
    (C.compare prediction observation = true ↔
      C.requiredComparison prediction outcome)

/-- Only compilation/runtime preservation belongs in this boundary. The Lean
judgment still contains concrete foreign calls, so this field does not assert
that project-owned marshalling or transport behavior is correct. The remaining
external ISA/kernel contracts are fixed by `Contract.external` and its ledger.
At instantiation these three laws must follow from a compiler/runtime theorem
parametric in the same concrete foreign semantics, preserving total termination;
none is permission to assume the shim implements the abstract transport. -/
structure Foundations {D : Domain} (C : Contract D)
    (E : Executions D) : Prop where
  nativeToLean : Refines C E.native E.lean
  leanReturnToNative :
    ∀ w q trace result, C.external w → C.admitted q →
      E.lean w q trace result → ∃ nativeTrace, E.native w q nativeTrace result
  terminationPreserved :
    ∀ w q, C.external w → C.admitted q →
      E.leanTerminates w q → E.nativeTerminates w q

/-- Each field is a proof obligation to discharge for the concrete code. These
must not become new axioms or external premises of the final instantiated result. -/
structure ComponentProofs {D : Domain} (C : Contract D)
    (E : Executions D) : Prop where
  leanToAbi : Refines C E.lean E.abi
  abiToProtocol : Refines C E.abi E.protocol
  protocolToHarness : Refines C E.protocol E.harness
  harnessCorrect : Safe C E.harness
  leanNoDivergence : NoDivergence C E.lean E.leanTerminates
  leanAvailability : Available C E.lean
  coverage : Covered C
  comparison : ComparisonCorrect C

/-- The statement to instantiate for the actual linked observer. -/
structure EndToEnd {D : Domain} (C : Contract D)
    (E : Executions D) : Prop where
  safety : Safe C E.native
  noDivergence : NoDivergence C E.native E.nativeTerminates
  availability : Available C E.native
  coverage : Covered C
  comparison : ComparisonCorrect C

/-- A composition theorem about the planning schema, not an observer proof. -/
theorem components_suffice {D : Domain} {C : Contract D} {E : Executions D}
    (foundation : Foundations C E) (parts : ComponentProofs C E) :
    EndToEnd C E where
  safety := by
    intro w q trace result external admitted native
    have lean := foundation.nativeToLean w q trace result external admitted native
    have abi := parts.leanToAbi w q trace result external admitted lean
    have protocol := parts.abiToProtocol w q trace result external admitted abi
    have harness := parts.protocolToHarness w q trace result external admitted protocol
    exact parts.harnessCorrect w q trace result external admitted harness
  noDivergence := by
    intro w q external admitted targetTerminates
    rcases parts.leanNoDivergence w q external admitted targetTerminates with
      ⟨leanTerminates, leanExists⟩
    refine ⟨foundation.terminationPreserved w q external admitted leanTerminates, ?_⟩
    obtain ⟨leanTrace, result, leanRun⟩ := leanExists
    obtain ⟨nativeTrace, nativeRun⟩ :=
      foundation.leanReturnToNative w q leanTrace result external admitted leanRun
    exact ⟨nativeTrace, result, nativeRun⟩
  availability := by
    intro w q external admitted targetTerminates available
    rcases parts.leanAvailability w q external admitted targetTerminates available with
      ⟨⟨leanTrace, observation, leanRun⟩, allLeanResults⟩
    constructor
    · obtain ⟨nativeTrace, nativeRun⟩ :=
        foundation.leanReturnToNative w q leanTrace (.observed observation)
          external admitted leanRun
      exact ⟨nativeTrace, observation, nativeRun⟩
    · intro trace result nativeRun
      exact allLeanResults trace result
        (foundation.nativeToLean w q trace result external admitted nativeRun)
  coverage := parts.coverage
  comparison := parts.comparison

/-- Logical check that the complete goal excludes an observer with no successes. -/
theorem end_to_end_excludes_no_success {D : Domain} {C : Contract D}
    {E : Executions D} (claim : EndToEnd C E) :
    ¬ (∀ w q trace observation, ¬ E.native w q trace (.observed observation)) := by
  intro none
  rcases claim.coverage.1 with ⟨c, required⟩
  rcases claim.coverage.2 c required with
    ⟨w, q, external, admitted, targetTerminates, available, _⟩
  rcases (claim.availability w q external admitted targetTerminates available).1 with
    ⟨trace, observation, executed⟩
  exact none w q trace observation executed

#check EndToEnd
#check EndToEnd.noDivergence
#check components_suffice
#check end_to_end_excludes_no_success
#print axioms components_suffice
#print axioms end_to_end_excludes_no_success

end ObserverEndToEndGoal
