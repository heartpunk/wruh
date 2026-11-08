import Bridge

namespace MovObserver.FaultProtocol
open Ayxg.QfAbv
open Bridge

/-- Original stop evidence, frozen before any capture redirection. `post` is
related to native acquisition by the bridge obligations, never a prediction.
Missing siginfo stays missing rather than being synthesized from an outcome. -/
structure FrozenStop where
  token : StopToken
  waitStatus : UInt32
  siginfo : Option (List (BitVec 8))
  post : Env Γ

inductive ObserverFailure where
  | transport (errno : UInt32)
  | captureFault (waitStatus : UInt32) (siginfo : Option (List (BitVec 8)))
  | missingState
  | invalidState
  | interrupted (waitStatus : UInt32)

/-- Capture may save fields before borrowing them. Saved state is meaningful
only for listed fields and must agree with the ORIGINAL stopped target state.
The modeled memory is framed separately; saving it cannot license corruption. -/
structure CaptureState where
  machine : Env Γ
  saved : Env Γ
  savedFields : List (Σ s : TermSort, Var Γ s)

/-- Every modeled field is either still intact or already faithfully saved.
Memory writes are confined independently of this field preservation alternative.
RIP also needs preservation/saving; redirection cannot erase the original PC. -/
def Recoverable (original : FrozenStop) (writes : List (BitVec 64))
    (s : CaptureState) : Prop :=
  (∀ (sort : TermSort) (field : Var Γ sort),
    (⟨sort, field⟩ : Σ t, Var Γ t) ≠ ⟨_, v_mem⟩ →
    ((⟨sort, field⟩ : Σ t, Var Γ t) ∈ s.savedFields →
      Env.lookup s.saved field = Env.lookup original.post field) ∧
    ((⟨sort, field⟩ : Σ t, Var Γ t) ∉ s.savedFields →
      Env.lookup s.machine field = Env.lookup original.post field)) ∧
  (∀ address, address ∉ writes →
    Env.lookup s.machine v_mem address = Env.lookup original.post v_mem address)

inductive CaptureEvent where
  | targetInvocation
  | captureStep
  | fallbackStep

/-- Prefixes start AFTER the one original target stop. No target invocation is
allowed in capture or fallback, including on an error path. Event completeness
must be established from concrete execution; relabeling a replay is not a proof. -/
def NoReplay (events : List CaptureEvent) : Prop :=
  ∀ event ∈ events, match event with
    | .targetInvocation => False
    | _ => True

inductive CaptureResult where
  | observed (original : FrozenStop) (values : Env Γ)
  | failed (original : FrozenStop) (reason : ObserverFailure)

/-- Receipts retain every intermediate state, including aborted capture prefixes.
A concrete trace binding must include those states and every target invocation. -/
structure CaptureRun where
  states : List CaptureState
  events : List CaptureEvent
  result : CaptureResult

/-- A failed observation still reports the same original stop. Required fields
and memory addresses must be fixed independently of capture success by the final
profile. Env is a typed carrier here: unselected values are not claimed observed.
Profile adequacy and nonvacuous coverage remain required integration obligations. -/
def ResultFaithful (requiredFields : List (Σ s : TermSort, Var Γ s))
    (requiredMemory : List (BitVec 64)) (original : FrozenStop) : CaptureResult → Prop
  | .observed recorded values => recorded = original ∧
      (∀ (sort : TermSort) (field : Var Γ sort),
        (⟨sort, field⟩ : Σ t, Var Γ t) ∈ requiredFields →
        Env.lookup values field = Env.lookup original.post field) ∧
      (∀ address ∈ requiredMemory,
        Env.lookup values v_mem address = Env.lookup original.post v_mem address)
  | .failed recorded _ => recorded = original

/-- Prefix preservation and original-outcome fidelity, independent of whether
normal capture or fallback completes. Acquisition, classification and failure
causality must be bound separately to the same native execution. -/
def FaultCaptureSafety (writes : List (BitVec 64))
    (requiredFields : List (Σ s : TermSort, Var Γ s))
    (requiredMemory : List (BitVec 64))
    (runs : FrozenStop → CaptureRun → Prop) : Prop :=
  ∀ original run, runs original run →
    run.states ≠ [] ∧ NoReplay run.events ∧
    (∀ state ∈ run.states, Recoverable original writes state) ∧
    ResultFaithful requiredFields requiredMemory original run.result

/-- A fallback starts from the EXACT interrupted capture state and frozen stop.
It cannot request another target run or replace original evidence with its own
later stop. All outcomes must be faithful, including failure. -/
def FallbackCorrect (writes : List (BitVec 64))
    (requiredFields : List (Σ s : TermSort, Var Γ s))
    (requiredMemory : List (BitVec 64))
    (capture : FrozenStop → CaptureRun → Prop)
    (fallback : FrozenStop → CaptureState → CaptureRun → Prop) : Prop :=
  ∀ original interrupted prior status info,
    capture original prior →
    prior.result = .failed original (.captureFault status info) →
    prior.states.getLast? = some interrupted →
    Recoverable original writes interrupted →
    (∃ run, fallback original interrupted run) ∧
    (∀ run, fallback original interrupted run →
      run.states.head? = some interrupted ∧ NoReplay run.events ∧
      (∀ state ∈ run.states, Recoverable original writes state) ∧
      ResultFaithful requiredFields requiredMemory original run.result)

end MovObserver.FaultProtocol
