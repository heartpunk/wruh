import FaultProtocol

namespace MovObserver.WholeObserver
open Ayxg.QfAbv
open Bridge FaultProtocol

/-- Finite caller input. No predicted target outcome is an input to observation.
The admitted platform/profile must independently validate exactly-one-instruction
encoding, feature support, mapping permissions and coverage; byte length alone
is not a decoder or a native admission proof. -/
structure Request where
  instruction : List (BitVec 8)
  entry : BitVec 64
  input : CapturedValues
  outputFields : List (Σ s : TermSort, Var Γ s)
  outputMemory : List (BitVec 64)

/-- Every supplied field/byte is installed exactly. Whole-array input fields
are forbidden; finite requested memory is expressed as address-byte pairs. -/
def InputInstalled (q : Request) (s : Env Γ) : Prop :=
  (∀ f ∈ q.input.fields,
    (⟨f.sort, f.field⟩ : Σ t, Var Γ t) ≠ ⟨_, v_mem⟩ ∧
    Env.lookup s f.field = f.value) ∧
  (∀ pair ∈ q.input.memory, Env.lookup s v_mem pair.1 = pair.2) ∧
  Env.lookup s v_rip = q.entry ∧
  0 < q.instruction.length ∧ q.instruction.length ≤ 15 ∧
  q.entry.toNat + q.instruction.length ≤ 2^64 ∧
  (∀ i : Fin q.instruction.length,
    Env.lookup s v_mem (BitVec.ofNat 64 (q.entry.toNat + i.val)) = q.instruction[i])

/-- Ghost events must be obtained from the complete actual execution, not
manufactured by the observer being checked. Concrete execution refinement must
account for every invocation, including restarts, and every fault/abort path. -/
inductive Event where
  | traceeReady (token : StopToken) (ambient : Env Γ)
  | installationPrefix (state : CaptureState)
  | targetStart (token : StopToken) (before : Env Γ)
  | targetStop (original : FrozenStop)
  | targetExit (tracee : Tracee) (waitStatus : UInt32)
  | capturePrefix (original : FrozenStop) (state : CaptureState)
  | transport (operation : Operation) (reply : Reply)

inductive Result where
  | captured (capture : CaptureResult)
  | setupFailed (reason : ObserverFailure)
  | targetExited (tracee : Tracee) (waitStatus : UInt32)
  | outcomeUnavailable (started : StopToken) (reason : ObserverFailure)

structure Execution (State : Type) where
  initial : Request → State
  step : State → State → Prop
  history : State → List Event
  returned : State → Option Result

def starts (events : List Event) : List (Env Γ) :=
  events.filterMap fun event => match event with
    | .targetStart _ before => some before
    | _ => none

def stops (events : List Event) : List FrozenStop :=
  events.filterMap fun event => match event with
    | .targetStop original => some original
    | _ => none

/-- Pure request consistency, independent of execution success. This catches
conflicting duplicate assignments and instruction/input overlap via InputInstalled.
It is not the full CPU/OS/permissions admission predicate. -/
def RequestCoherent (q : Request) : Prop :=
  (∃ state, InputInstalled q state) ∧
  (⟨_, v_mem⟩ : Σ s, Var Γ s) ∉ q.outputFields ∧
  q.outputFields.Nodup ∧ q.outputMemory.Nodup

inductive Phase where
  | ready
  | preparing (token : StopToken) (ambient : Env Γ)
  | running (token : StopToken)
  | stopped (original : FrozenStop)
  | exited (tracee : Tracee) (waitStatus : UInt32)

/-- Ordered native occurrence skeleton. One start, matching later stop/exit,
and capture only after that exact stop. Transport events cannot stand in for
missing target events in the eventual complete execution binding. -/
inductive Ordered : List Event → Phase → Prop
  | initial : Ordered [] .ready
  | transport {events phase} (operation reply) : Ordered events phase →
      Ordered (events ++ [.transport operation reply]) phase
  | prepared {events} (token ambient) : Ordered events .ready →
      Ordered (events ++ [.traceeReady token ambient]) (.preparing token ambient)
  | installing {events token ambient} (state) : Ordered events (.preparing token ambient) →
      Ordered (events ++ [.installationPrefix state]) (.preparing token ambient)
  | start {events token ambient} (before) : Ordered events (.preparing token ambient) →
      Ordered (events ++ [.targetStart token before]) (.running token)
  | stop {events token} (original : FrozenStop) :
      Ordered events (.running token) →
      original.evidence.token.tracee = token.tracee →
      token.serial < original.evidence.token.serial →
      Ordered (events ++ [.targetStop original]) (.stopped original)
  | exit {events token} (status) : Ordered events (.running token) →
      Ordered (events ++ [.targetExit token.tracee status]) (.exited token.tracee status)
  | capture {events original} (state) : Ordered events (.stopped original) →
      Ordered (events ++ [.capturePrefix original state]) (.stopped original)

def ReturnFaithful (q : Request) (events : List Event) : Result → Prop
  | .setupFailed _ => Ordered events .ready ∨ ∃ token ambient, Ordered events (.preparing token ambient)
  | .captured result =>
      ∃ original, Ordered events (.stopped original) ∧
        ResultFaithful q.outputFields q.outputMemory original result
  | .targetExited tracee status => Ordered events (.exited tracee status)
  | .outcomeUnavailable started _ => Ordered events (.running started)

/-- Whole-run finite completion, including orchestration retries and concrete
foreign calls. Apply conditionally to the agreed external progress assumptions
and terminating target instruction, never assume termination of our own code.
This is stronger than the existing per-call termination obligation. -/
def Terminates {State : Type} (e : Execution State) (q : Request) : Prop :=
  Acc (fun next current => e.step current next) (e.initial q) ∧
  ∀ s, Reaches e.step (e.initial q) s →
    match e.returned s with
    | none => ∃ next, e.step s next
    | some _ => ¬ ∃ next, e.step s next

/-- Records cannot erase earlier execution or lose a target replay. All reachable
prefixes have at most one invocation. Source-to-event completeness remains an
obligation of the actual execution binding, not an assumption of instrumentation. -/
def TraceConsistent {State : Type} (e : Execution State) (q : Request) : Prop :=
  e.history (e.initial q) = [] ∧
  ∀ s, Reaches e.step (e.initial q) s →
    (∃ phase, Ordered (e.history s) phase) ∧
    (∀ token before, Event.targetStart token before ∈ e.history s → InputInstalled q before) ∧
    (∀ next, e.step s next → ∃ suffix,
      e.history next = e.history s ++ suffix)

/-- Successful-capture availability is separate from safety and termination.
Under the fixed successful-capture environment/profile it excludes fail-all,
including implementations that always return setupFailed. -/
def CaptureAvailable {State : Type} (e : Execution State) (q : Request) : Prop :=
  (∃ s stop values, Reaches e.step (e.initial q) s ∧
    e.returned s = some (.captured (.observed stop values))) ∧
  (∀ s result, Reaches e.step (e.initial q) s → e.returned s = some result →
    ∃ stop values, result = .captured (.observed stop values))

/-- Composition-facing fidelity/termination obligation, not yet the complete
native noninterference contract. Missing: actual Lean/ABI/hardware event binding,
installation and capture prefix frames, source of external progress premises,
profile adequacy, failure causality and full FP representation. None is replaced
by an arbitrary `correct` premise or an AYXG/native comparison. -/
def ObserverFidelityAndTermination {State : Type}
    (e : Execution State) (q : Request) : Prop :=
  Terminates e q ∧ TraceConsistent e q ∧
  (¬ RequestCoherent q →
    ∀ s result, Reaches e.step (e.initial q) s → e.returned s = some result →
      result = .setupFailed .invalidState) ∧
  ∀ s result, Reaches e.step (e.initial q) s → e.returned s = some result →
    ReturnFaithful q (e.history s) result

/-- Fixed layout, chosen before observing execution. Protected-set adequacy
must be established from mappings and target-visible state. Private preparation
writes cannot silently become target input; capture cannot overwrite input/code. -/
structure Layout where
  privateInstall : List (BitVec 64)
  captureWrites : List (BitVec 64)
  protectedAddress : BitVec 64 → Prop

def codeAddresses (q : Request) : List (BitVec 64) :=
  (List.range q.instruction.length).map fun i => BitVec.ofNat 64 (q.entry.toNat + i)

def installationFields (q : Request) : List (Σ s : TermSort, Var Γ s) :=
  [⟨_, v_mem⟩, ⟨_, v_rip⟩] ++ q.input.fields.map (fun f => ⟨f.sort, f.field⟩)

def installationWrites (q : Request) (layout : Layout) : List (BitVec 64) :=
  q.input.memory.map Prod.fst ++ codeAddresses q ++ layout.privateInstall

def LayoutSeparated (q : Request) (layout : Layout) : Prop :=
  (∀ address ∈ layout.privateInstall,
    address ∉ q.input.memory.map Prod.fst ∧ address ∉ codeAddresses q ∧
    ¬ layout.protectedAddress address) ∧
  (∀ address ∈ layout.captureWrites,
    address ∉ q.input.memory.map Prod.fst ∧ address ∉ codeAddresses q ∧
    ¬ layout.protectedAddress address)

/-- Intermediate installation may borrow nonrequested fields only while their
original ambient values remain recoverable. Requested fields may change to their
requested values. Strict restoration is separately required at target entry. -/
def InstallationRecoverable (q : Request) (layout : Layout)
    (ambient : Env Γ) (state : CaptureState) : Prop :=
  (∀ (sort : TermSort) (field : Var Γ sort),
    (⟨sort, field⟩ : Σ t, Var Γ t) ∉ installationFields q →
    ((⟨sort, field⟩ : Σ t, Var Γ t) ∈ state.savedFields →
      Env.lookup state.saved field = Env.lookup ambient field) ∧
    ((⟨sort, field⟩ : Σ t, Var Γ t) ∉ state.savedFields →
      Env.lookup state.machine field = Env.lookup ambient field)) ∧
  (∀ address, address ∉ installationWrites q layout →
    Env.lookup state.machine v_mem address = Env.lookup ambient v_mem address)

/-- The same ordered event history supplies the original installation state and
frozen target stop. Every exposed prefix, including one ending in a fault, must
satisfy its frame/recoverability obligation. No separate successful-run trace is
substituted. Concrete execution binding must expose intermediate effects. -/
def PrefixNoninterference (q : Request) (layout : Layout) (events : List Event) : Prop :=
  LayoutSeparated q layout ∧
  (∀ prefix suffix token ambient state,
    Ordered prefix (.preparing token ambient) →
    events = prefix ++ Event.installationPrefix state :: suffix →
    InstallationRecoverable q layout ambient state) ∧
  (∀ prefix suffix token ambient before,
    Ordered prefix (.preparing token ambient) →
    events = prefix ++ Event.targetStart token before :: suffix →
    StateFrame (installationFields q) (installationWrites q layout) ambient before) ∧
  (∀ original state, Event.capturePrefix original state ∈ events →
    Recoverable original layout.captureWrites state)

/-- Prefix framing is required on every reachable state, even if no successful
capture ever returns. Host memory/ABI framing remains the separate bridge contract.
This does not assert that arbitrary omitted hardware state is represented by Γ. -/
def ObserverPrefixNoninterference {State : Type} (e : Execution State)
    (q : Request) (layout : Layout) : Prop :=
  ∀ s, Reaches e.step (e.initial q) s → PrefixNoninterference q layout (e.history s)

/-- Both obligations apply to exactly the same execution and request. This is
a composition obligation only; native binding, complete profile and component
linkage must still be discharged, rather than assumed from this conjunction. -/
def ObserverCoreContract {State : Type} (e : Execution State)
    (q : Request) (layout : Layout) : Prop :=
  ObserverFidelityAndTermination e q ∧ ObserverPrefixNoninterference e q layout

end MovObserver.WholeObserver
