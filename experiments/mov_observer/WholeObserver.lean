import FaultProtocol

namespace MovObserver.WholeObserver
open Ayxg.QfAbv
open Bridge FaultProtocol

/-- One half-open byte range [start, endExclusive). Natural endpoints allow
endExclusive = 2^64 without wrapping the last address back to zero. -/
structure MemoryRange where
  start : Nat
  endExclusive : Nat
  bytes : Array (BitVec 8)
  ordered : start ≤ endExclusive
  bounded : endExclusive ≤ 2^64
  size_eq : bytes.size = endExclusive - start

/-- Finite sparse image. List order is only serialization order; ranges must
not overlap. There is no size, placement or operand-derived restriction beyond
fitting the architecture's address space. -/
structure SparseMemoryImage where
  ranges : List MemoryRange
  nonoverlapping : ranges.Pairwise (fun a b =>
    a.endExclusive ≤ b.start ∨ b.endExclusive ≤ a.start)

/-- Reuse the existing byte-addressed memory/frame vocabulary. Range validity
ensures each indexed address is in bounds; conversion does not wrap any byte. -/
def SparseMemoryImage.byteWrites (image : SparseMemoryImage) :
    List (BitVec 64 × BitVec 8) :=
  image.ranges.flatMap fun r =>
    r.bytes.toList.zipIdx.map fun (byte, i) =>
      (BitVec.ofNat 64 (r.start + i), byte)

def SparseMemoryImage.addresses (image : SparseMemoryImage) : List (BitVec 64) :=
  image.byteWrites.map Prod.fst

structure InputState where
  fields : List CapturedField
  memory : SparseMemoryImage

/-- Finite caller input. No predicted target outcome is an input to observation.
The admitted platform/profile must independently validate exactly-one-instruction
encoding, feature support, mapping permissions and coverage; byte length alone
is not a decoder or a native admission proof. -/
structure Request where
  instruction : List (BitVec 8)
  entry : BitVec 64
  input : InputState
  outputFields : List (Σ s : TermSort, Var Γ s)
  outputMemory : List (BitVec 64)

/-- Every supplied field/byte is installed exactly. Whole-array input fields
are forbidden; every byte of every supplied sparse range is required. -/
def InputInstalled (q : Request) (s : Env Γ) : Prop :=
  (∀ f ∈ q.input.fields,
    (⟨f.sort, f.field⟩ : Σ t, Var Γ t) ≠ ⟨_, v_mem⟩ ∧
    Env.lookup s f.field = f.value) ∧
  (∀ pair ∈ q.input.memory.byteWrites, Env.lookup s v_mem pair.1 = pair.2) ∧
  Env.lookup s v_rip = q.entry ∧
  0 < q.instruction.length ∧ q.instruction.length ≤ 15 ∧
  q.entry.toNat + q.instruction.length ≤ 2^64 ∧
  (∀ i : Fin q.instruction.length,
    Env.lookup s v_mem (BitVec.ofNat 64 (q.entry.toNat + i.val)) = q.instruction[i])

/-- Ghost events must be obtained from the complete actual execution, not
manufactured by the observer being checked. Concrete execution refinement must
account for every invocation, including restarts, and every fault/abort path. -/
inductive Event where
  | traceeCreated (tracee : Tracee)
  | traceeReady (token : StopToken) (ambient : Env Γ)
  | installationPrefix (state : CaptureState)
  | targetStart (token : StopToken) (before : Env Γ)
  | targetStop (original : FrozenStop)
  | targetExit (tracee : Tracee) (waitStatus : UInt32)
  | capturePrefix (original : FrozenStop) (state : CaptureState)
  | transport (operation : Operation) (reply : Reply)
  | runtimeError (operation : Operation) (error : IO.Error)

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

/-- Pure request consistency, independent of execution success. This catches
conflicting duplicate assignments and instruction/input overlap via InputInstalled.
It is not the full CPU/OS/permissions admission predicate. -/
def RequestCoherent (q : Request) : Prop :=
  (∃ state, InputInstalled q state) ∧
  (⟨_, v_mem⟩ : Σ s, Var Γ s) ∉ q.outputFields ∧
  q.outputFields.Nodup ∧ q.outputMemory.Nodup

inductive Phase where
  | ready
  | created (tracee : Tracee)
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
  | runtimeError {events phase} (operation error) : Ordered events phase →
      Ordered (events ++ [.runtimeError operation error]) phase
  | created {events} (tracee) : Ordered events .ready →
      Ordered (events ++ [.traceeCreated tracee]) (.created tracee)
  | prepared {events tracee} (token ambient) : Ordered events (.created tracee) →
      token.tracee = tracee →
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

def SetupPhase : Phase → Prop
  | .ready | .created _ | .preparing _ _ => True
  | _ => False

def ReturnFaithful (q : Request) (events : List Event) : Result → Prop
  | .setupFailed _ => ∃ phase, SetupPhase phase ∧ Ordered events phase
  | .captured result =>
      ∃ original, Ordered events (.stopped original) ∧
        ResultFaithful q.outputFields q.outputMemory original result
  | .targetExited tracee status => Ordered events (.exited tracee status)
  | .outcomeUnavailable started _ => Ordered events (.running started)

/-- Which process a concrete bridge call addresses; create has no process yet. -/
def operationTracee : Operation → Option Tracee
  | .create => none
  | .readRegisters stop | .writeRegisters stop _ |
    .readMemory stop _ _ | .writeMemory stop _ _ | .singleStep stop => some stop.tracee
  | .wait tracee | .reap tracee => some tracee

/-- Exact syscall error in the same execution phase and for its tracee. The
bridge refinement must establish errno authenticity; this relation prevents
borrowing an error from another process or an earlier execution phase. -/
def TransportErrorAt (events : List Event) (phase : Phase) (errno : UInt32) : Prop :=
  ∃ before after operation transferred,
    events = before ++ Event.transport operation (.failed errno transferred) :: after ∧
    Ordered before phase ∧
    match phase with
    | .ready => operationTracee operation = none
    | .created tracee => operationTracee operation = some tracee
    | .preparing stop _ | .running stop => operationTracee operation = some stop.tracee
    | .stopped original => operationTracee operation = some original.evidence.token.tracee
    | .exited tracee _ => operationTracee operation = some tracee

/-- Preserve the exact returned IO.Error from the originating operation and
phase. A Lean IO error is not inferred to be a native errno or a runtime abort. -/
def RuntimeErrorAt (events : List Event) (phase : Phase) (error : IO.Error) : Prop :=
  ∃ before after operation,
    events = before ++ Event.runtimeError operation error :: after ∧
    Ordered before phase ∧
    match phase with
    | .ready => operationTracee operation = none
    | .created tracee => operationTracee operation = some tracee
    | .preparing stop _ | .running stop => operationTracee operation = some stop.tracee
    | .stopped original => operationTracee operation = some original.evidence.token.tracee
    | .exited tracee _ => operationTracee operation = some tracee

/-- Native transport and returned IO errors retain evidence from their own
phase. Other failure categories still need their concrete classification;
True in those branches asserts nothing about their causes. Retry/abort policy
is user-controlled and is not chosen by this relation. -/
def TransportFailureSupported (events : List Event) : Result → Prop
  | .setupFailed (.transport errno) =>
      ∃ phase, SetupPhase phase ∧ Ordered events phase ∧
        TransportErrorAt events phase errno
  | .captured (.failed evidence (.transport errno)) =>
      ∃ original, original.evidence = evidence ∧
        TransportErrorAt events (.stopped original) errno
  | .outcomeUnavailable started (.transport errno) =>
      TransportErrorAt events (.running started) errno
  | .setupFailed (.runtimeError error) =>
      ∃ phase, SetupPhase phase ∧ Ordered events phase ∧ RuntimeErrorAt events phase error
  | .captured (.failed evidence (.runtimeError error)) =>
      ∃ original, original.evidence = evidence ∧
        RuntimeErrorAt events (.stopped original) error
  | .outcomeUnavailable started (.runtimeError error) =>
      RuntimeErrorAt events (.running started) error
  | _ => True

/-- A target stop is supported by the exact consolidated wait receipt from
its running phase. The receipt retains optional siginfo without synthesizing it.
This does not classify the stop as successful instruction completion or establish
the native acquisition of `original.post`; those obligations remain separate. -/
def TargetStopReceipt (priorEvents : List Event) (original : FrozenStop) : Prop :=
  ∃ before after started,
    Ordered before (.running started) ∧
    started.tracee = original.evidence.token.tracee ∧
    priorEvents = before ++
      Event.transport (.wait started.tracee)
        (.stopped original.evidence.token original.evidence.waitStatus
          original.evidence.siginfo) :: after

/-- Exit evidence is the exact wait receipt for the same running tracee, not
an unrelated transport status or a status taken from a later observer process. -/
def TargetExitReceipt (priorEvents : List Event) (tracee : Tracee)
    (status : UInt32) : Prop :=
  ∃ before after started,
    Ordered before (.running started) ∧ started.tracee = tracee ∧
    priorEvents = before ++
      Event.transport (.wait tracee) (.exited tracee status) :: after

/-- Connect bridge receipts and target-outcome events within the SAME complete
history. Receipt witnesses precede the outcome event; no immediate adjacency is
required. Ordered supplies the single-invocation phase discipline. This evidence
link is necessary but does not replace concrete bridge/native trace refinement. -/
def TransportEvidenceLinked (events : List Event) : Prop :=
  (∀ operation reply, Event.transport operation reply ∈ events →
    OperationReplyCompatible operation reply) ∧
  (∀ priorEvents suffix original,
    events = priorEvents ++ Event.targetStop original :: suffix →
    TargetStopReceipt priorEvents original) ∧
  (∀ priorEvents suffix tracee status,
    events = priorEvents ++ Event.targetExit tracee status :: suffix →
    TargetExitReceipt priorEvents tracee status)

/-- Apply the receipt linkage to every reachable prefix, including paths which
later fail. It uses the same Execution as fidelity and prefix noninterference. -/
def ObserverTransportEvidence {State : Type} (e : Execution State)
    (q : Request) : Prop :=
  ∀ s, Reaches e.step (e.initial q) s → TransportEvidenceLinked (e.history s)

/-- Nonexceptional whole-run finite completion, including agreed retries and
concrete foreign calls. Exceptional substrate crashes are outside this obligation. Apply conditionally to the agreed external progress assumptions
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
    ReturnFaithful q (e.history s) result ∧ TransportFailureSupported (e.history s) result

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
  q.input.memory.addresses ++ codeAddresses q ++ layout.privateInstall

def LayoutSeparated (q : Request) (layout : Layout) : Prop :=
  (∀ address ∈ layout.privateInstall,
    address ∉ q.input.memory.addresses ∧ address ∉ codeAddresses q ∧
    ¬ layout.protectedAddress address) ∧
  (∀ address ∈ layout.captureWrites,
    address ∉ q.input.memory.addresses ∧ address ∉ codeAddresses q ∧
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
  (∀ priorEvents suffix token ambient state,
    Ordered priorEvents (.preparing token ambient) →
    events = priorEvents ++ Event.installationPrefix state :: suffix →
    InstallationRecoverable q layout ambient state) ∧
  (∀ priorEvents suffix token ambient before,
    Ordered priorEvents (.preparing token ambient) →
    events = priorEvents ++ Event.targetStart token before :: suffix →
    StateFrame (installationFields q) (installationWrites q layout) ambient before) ∧
  (∀ original state, Event.capturePrefix original state ∈ events →
    Recoverable original layout.captureWrites state)

/-- Prefix framing is required on every reachable state, even if no successful
capture ever returns. Host memory/ABI framing remains the separate bridge contract.
This does not assert that arbitrary omitted hardware state is represented by Γ. -/
def ObserverPrefixNoninterference {State : Type} (e : Execution State)
    (q : Request) (layout : Layout) : Prop :=
  ∀ s, Reaches e.step (e.initial q) s → PrefixNoninterference q layout (e.history s)

/-- The exact selected output representation of a state. Selection is fixed by
 the request, independently of whether any execution or capture succeeds. -/
def selectedValues (request : Request) (state : Env Γ) : CapturedValues where
  fields := request.outputFields.map (fun ⟨sort, field⟩ =>
    ⟨sort, field, Env.lookup state field⟩)
  memory := request.outputMemory.map (fun a => (a, Env.lookup state v_mem a))

/-- The specification fixes outputQ and recover, independently of the observer.
Selected outputs must retain exactly its state distinctions and recover its class.
An empty selection cannot satisfy this for a nontrivial quotient, even if all
executions fail. This is representation completeness, not capture availability. -/
def OutputCoverage (request : Request) (outputQ : Setoid (Env Γ))
    (recover : CapturedValues → Option (Quotient outputQ)) : Prop :=
  (∀ s t, selectedValues request s = selectedValues request t ↔ outputQ.r s t) ∧
  (∀ s, recover (selectedValues request s) = some (Quotient.mk outputQ s))

/-- Recovery concerns the actual returned record and the original target stop
in the same execution history, not merely an ideal record or a predicted state. -/
def ObserverOutputComplete {State : Type} (e : Execution State)
    (request : Request) (outputQ : Setoid (Env Γ))
    (recover : CapturedValues → Option (Quotient outputQ)) : Prop :=
  OutputCoverage request outputQ recover ∧
  ∀ s recorded values,
    Reaches e.step (e.initial request) s →
    e.returned s = some (.captured (.observed recorded values)) →
    ∃ original,
      Ordered (e.history s) (.stopped original) ∧
      recorded = original.evidence ∧
      values = selectedValues request original.post ∧
      recover values = some (Quotient.mk outputQ original.post)

/-- These obligations apply to the same execution, request and fixed output
quotient. Native binding and component linkage remain separate obligations. -/
def ObserverCoreContract {State : Type} (e : Execution State)
    (q : Request) (layout : Layout) (outputQ : Setoid (Env Γ))
    (recover : CapturedValues → Option (Quotient outputQ)) : Prop :=
  ObserverFidelityAndTermination e q ∧ ObserverPrefixNoninterference e q layout ∧
    ObserverTransportEvidence e q ∧ ObserverOutputComplete e q outputQ recover

end MovObserver.WholeObserver
