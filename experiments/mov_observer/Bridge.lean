import NativeBoundary

namespace MovObserver.Bridge
open Ayxg.QfAbv
open NativeBoundary

/-- A process identity includes a generation to prevent PID-reuse confusion.
The bridge must establish it when creating/attaching; this is not a kernel PID. -/
structure Tracee where
  pid : UInt32
  generation : Nat
  deriving DecidableEq

/-- An observation is tied to a particular stop of a particular process. -/
structure StopToken where
  tracee : Tracee
  serial : Nat
  deriving DecidableEq

inductive Operation where
  | create
  | readRegisters (stop : StopToken)
  | writeRegisters (stop : StopToken) (bytes : List (BitVec 8))
  | readMemory (stop : StopToken) (address : BitVec 64) (length : Nat)
  | writeMemory (stop : StopToken) (address : BitVec 64) (bytes : List (BitVec 8))
  | singleStep (stop : StopToken)
  | wait (tracee : Tracee)
  | reap (tracee : Tracee)

/-- Preserve errno, wait status and siginfo as transport evidence. Classification
belongs to the protocol; a signal is not inferred to be target completion here. -/
inductive Reply where
  | created (tracee : Tracee)
  | bytes (stop : StopToken) (payload : List (BitVec 8))
  | written (stop : StopToken) (count : Nat)
  | resumed (prior : StopToken)
  | stopped (stop : StopToken) (waitStatus : UInt32) (siginfo : Option (List (BitVec 8)))
  | exited (tracee : Tracee) (waitStatus : UInt32)
  | reaped (tracee : Tracee)
  | failed (errno : UInt32) (transferred : Nat)

/-- Request/reply shape, identity and transfer-count compatibility. This is a
necessary boundary obligation, not evidence that the operation occurred. In
particular, a wait reply's new stop serial must additionally satisfy the live
tracee lifecycle contract; no previous serial is carried by `wait` itself.
A failed transfer may report a prefix, but non-transfer operations report zero.
The actual prefix bytes and effects are constrained separately by Transfer. -/
def OperationReplyCompatible (request : Operation) (reply : Reply) : Prop :=
  match request, reply with
  | .create, .created _ => True
  | .readRegisters stop, .bytes actual bytes => actual = stop ∧ bytes.length = 216
  | .writeRegisters stop bytes, .written actual count =>
      actual = stop ∧ bytes.length = 216 ∧ count = bytes.length
  | .readMemory stop _ length, .bytes actual bytes =>
      actual = stop ∧ bytes.length = length
  | .writeMemory stop _ bytes, .written actual count =>
      actual = stop ∧ count = bytes.length
  | .singleStep stop, .resumed actual => actual = stop
  | .wait tracee, .stopped stop _ _ => stop.tracee = tracee
  | .wait tracee, .exited actual _ => actual = tracee
  | .reap tracee, .reaped actual => actual = tracee
  | .readRegisters _, .failed _ count => count ≤ 216
  | .writeRegisters _ bytes, .failed _ count => count ≤ bytes.length
  | .readMemory _ _ length, .failed _ count => count ≤ length
  | .writeMemory _ _ bytes, .failed _ count => count ≤ bytes.length
  | .create, .failed _ count
  | .singleStep _, .failed _ count
  | .wait _, .failed _ count
  | .reap _, .failed _ count => count = 0
  | _, _ => False

/-- A successful foreign IO return may still fail wire validation. Retain the
exact malformed bytes rather than fabricating a native reply or IO.Error. -/
inductive DecodedReply where
  | reply (value : Reply)
  | malformed (bytes : ByteArray)

/-- Proposed narrow Lean effect boundary. No implementation or correctness law
is supplied. The concrete exported foreign symbol must implement this function
through the separately specified marshalling and ownership obligations. -/
structure ForeignAPI where
  invoke : Operation → IO DecodedReply

/-- Host addresses are distinct from tracee addresses. Length uses Nat so the
ABI obligation must rule out overflow before narrowing to a machine size. -/
structure Buffer where
  base : Nat
  length : Nat
  alignment : Nat
  owner : Nat
  generation : Nat
  deriving DecidableEq

abbrev HostMemory := Nat → BitVec 8

def BufferContains (b : Buffer) (a : Nat) : Prop :=
  b.base ≤ a ∧ a < b.base + b.length

def BufferValid (b : Buffer) : Prop :=
  b.base < 2^64 ∧ 0 < b.alignment ∧ b.base % b.alignment = 0 ∧
  b.base + b.length ≤ 2^64

def BuffersDisjoint (a b : Buffer) : Prop :=
  a.base + a.length ≤ b.base ∨ b.base + b.length ≤ a.base

/-- Exact bytes, not a hash or a relation chosen by an implementation. -/
def BufferBytes (b : Buffer) (memory : HostMemory) (bytes : List (BitVec 8)) : Prop :=
  bytes.length = b.length ∧
  ∀ i : Fin bytes.length, memory (b.base + i.val) = bytes[i]

/-- All host writes stay in the explicitly owned output buffers. This does not
license writes to tracee memory or assume any Lean object representation. -/
def HostFrame (outputs : List Buffer) (before after : HostMemory) : Prop :=
  ∀ a, (∀ b ∈ outputs, ¬ BufferContains b a) → after a = before a

/-- Entry-state check only; full-call lifetime is CallBufferLifetime below.
Distinct owner IDs do not imply disjoint storage. -/
def CallBuffersValid (inputs outputs : List Buffer) (liveOwners : List Nat) : Prop :=
  (∀ b ∈ inputs ++ outputs, BufferValid b ∧ b.owner ∈ liveOwners) ∧
  (∀ i ∈ inputs, ∀ o ∈ outputs, BuffersDisjoint i o) ∧
  outputs.Pairwise BuffersDisjoint

/-- Explicit host allocation state; an owner identifies the whole allocation,
not merely a permission label. Buffers refer to that allocation or a subrange. -/
structure HostState where
  memory : HostMemory
  allocations : Nat → Option Buffer
  retired : Nat → Nat → Prop
  writablePayload : Nat → Nat → List Buffer

def BorrowedFrom (b : Buffer) (h : HostState) : Prop :=
  ∃ allocation, h.allocations b.owner = some allocation ∧
    allocation.owner = b.owner ∧ allocation.generation = b.generation ∧
    ¬ h.retired b.owner b.generation ∧ BufferValid allocation ∧ BufferValid b ∧
    allocation.base ≤ b.base ∧
    b.base + b.length ≤ allocation.base + allocation.length

/-- Writable payload is supplied by the concrete allocation/ABI layout, not
chosen from observed writes. Every permitted slice must stay within the same
live allocation. Headers may be writable only as explicitly owned runtime
scratch, never by pretending they are returned observation bytes. -/
def WritableBorrow (b : Buffer) (h : HostState) : Prop :=
  BorrowedFrom b h ∧
  ∃ payload ∈ h.writablePayload b.owner b.generation,
    payload.owner = b.owner ∧ payload.generation = b.generation ∧
    BorrowedFrom payload h ∧ payload.base ≤ b.base ∧
    b.base + b.length ≤ payload.base + payload.length

/-- Required at every allocation/free transition: retired incarnations never
return. The concrete execution binding must expose each allocation/free event;
a step that hides free-and-reallocate is not an adequate binding. -/
def AllocationTransitionCorrect (before after : HostState) : Prop :=
  (∀ owner generation, before.retired owner generation →
    after.retired owner generation) ∧
  (∀ owner old, before.allocations owner = some old →
    after.allocations owner ≠ some old → after.retired owner old.generation) ∧
  (∀ owner allocation, after.allocations owner = some allocation →
    allocation.owner = owner ∧ ¬ after.retired owner allocation.generation)

/-- Live allocations cannot overlap; this includes allocations not passed to
the call (for example other Lean objects). Object headers and runtime metadata
must not be included in a writable payload slice. Their concrete locations
remain part of the future Lean ABI layout binding. -/
def AllocationsSeparated (h : HostState) : Prop :=
  ∀ a b left right,
    h.allocations a = some left → h.allocations b = some right → a ≠ b →
    BuffersDisjoint left right

/-- The same request and stop token must survive argument marshalling. Neither
an observed value nor another process's state may replace a requested value.
`encode`/`decode` are future concrete bridge codecs, not trusted premises. -/
def RequestCodecCorrect {Wire : Type}
    (encode : Operation → Wire) (decode : Wire → Option Operation) : Prop :=
  ∀ request, decode (encode request) = some request

/-- Symmetric output requirement, including transport errors and partial writes.
An implementation may not turn a failure into a fabricated observation. -/
def ReplyCodecCorrect {Wire : Type}
    (encode : Reply → Wire) (decode : Wire → Option Reply) : Prop :=
  ∀ reply, decode (encode reply) = some reply

/-- State of the future concrete execution interpreter. The relation must be
bound to the actual Lean program plus its concrete foreign implementation;
replacing it by an ideal protocol relation would not discharge these goals. -/
structure Execution (State : Type) where
  initial : Operation → State
  step : State → State → Prop
  returned : State → Option (Except IO.Error DecodedReply)
  /-- Complete ordered host writes for this step, including writes later undone.
  Completeness must follow from concrete bridge execution, not instrumentation
  that is permitted to omit effects. -/
  writes : State → State → List (Nat × BitVec 8)

inductive Reaches {State : Type} (step : State → State → Prop) : State → State → Prop
  | refl (s) : Reaches step s s
  | next {a b c} : Reaches step a b → step b c → Reaches step a c

/-- Every state of the call keeps the same backing allocations for borrowed
buffers, including the return state. Release/transfer of ownership happens only
after this borrowing interval; a bridge requiring a different ownership mode
must specify that mode rather than silently use this contract. -/
def CallBufferLifetime {State : Type} (e : Execution State)
    (host : State → HostState) (request : Operation) (buffers : List Buffer) : Prop :=
  ∀ s, Reaches e.step (e.initial request) s →
    AllocationsSeparated (host s) ∧
    ∀ b ∈ buffers,
      BorrowedFrom b (host s) ∧
      (host s).allocations b.owner = (host (e.initial request)).allocations b.owner

/-- Prefix-level host framing, including unsuccessful calls. Input contents
remain unchanged and every individual bridge step stays inside output or
separately declared, state-indexed scratch slices. Outputs are also state-indexed
so new payloads need not exist at call entry. Every slice must already be live
and writable in the PRE-state of a write; a later allocation cannot justify it.
The runtime allocation event must precede use, and allocation/header writes need
their own accounted runtime permission. Scratch is disjoint from
input/output slices. Every concrete write must occur in `e.writes`; equality of
endpoint bytes alone cannot discharge that execution-binding obligation.
Scratch allocation/free must be exposed as separate steps before/after use.
Operation-specific output contents/counts are separate obligations; this frame
is not permission to fabricate an output payload. -/
def CallDynamicMemoryFrame {State : Type} (e : Execution State)
    (host : State → HostState) (request : Operation) (inputs : List Buffer)
    (outputs scratch : State → List Buffer) : Prop :=
  ∀ s, Reaches e.step (e.initial request) s →
    (∀ b ∈ inputs, ∀ a, BufferContains b a →
      (host s).memory a = (host (e.initial request)).memory a) ∧
    (∀ b ∈ outputs s ++ scratch s, WritableBorrow b (host s)) ∧
    (∀ b ∈ scratch s, ∀ other ∈ inputs ++ outputs s, BuffersDisjoint b other) ∧
    (∀ next, e.step s next →
      HostFrame (outputs s ++ scratch s) (host s).memory (host next).memory ∧
      (∀ write ∈ e.writes s next,
        (∃ b ∈ outputs s ++ scratch s, BufferContains b write.1) ∧
        (∀ b ∈ inputs, ¬ BufferContains b write.1)) ∧
      AllocationTransitionCorrect (host s) (host next))

/-- Original preallocated-output contract as the constant-output instance.
This preserves its conditions; allocating a returned payload during the call
instead requires CallDynamicMemoryFrame with live state-indexed output slices.
Those slices must be fixed by runtime ownership/layout, never selected after
observing which addresses were written. -/
def CallMemoryFrame {State : Type} (e : Execution State)
    (host : State → HostState) (request : Operation) (inputs outputs : List Buffer)
    (scratch : State → List Buffer) : Prop :=
  CallDynamicMemoryFrame e host request inputs (fun _ => outputs) scratch

/-- No infinite path, stuck nonterminal state, or execution past return.
This is intentionally stronger than existence of one terminating execution.
External primitive progress and target termination are premises of the future
instantiated theorem; they are not assumed of project-owned code here. -/
def CallTerminates {State : Type} (e : Execution State) (request : Operation) : Prop :=
  Acc (fun next current => e.step current next) (e.initial request) ∧
  ∀ s, Reaches e.step (e.initial request) s →
    match e.returned s with
    | none => ∃ next, e.step s next
    | some _ => ¬ ∃ next, e.step s next

/-- Successful IO returns contain replies; returned IO errors remain terminal
through CallTerminates and must retain their identity in whole-run handling.
Every reachable returned reply belongs to its originating request. This
quantifies over all returned executions, including errors, without asserting
that the execution relation is already bound to the foreign implementation. -/
def CallReplyCompatibleFor {State : Type} (e : Execution State) (request : Operation) : Prop :=
  ∀ state reply,
    Reaches e.step (e.initial request) state →
    e.returned state = some (.ok (.reply reply)) → OperationReplyCompatible request reply

/-- Interface-wide claim retained separately from an admitted individual call. -/
def CallReplyCompatible {State : Type} (e : Execution State) : Prop :=
  ∀ request, CallReplyCompatibleFor e request

/-- Interface-level obligations only. Still required: bind Execution to the
actual ForeignAPI implementation and prove syscall argument/return, ownership,
process identity, transfer, and error semantics. Codec round trips do not prove
that the kernel saw those values, or that two matching codecs use the right ABI. -/
def BridgeCodecContract {RequestWire ReplyWire : Type}
    (encodeRequest : Operation → RequestWire)
    (decodeRequest : RequestWire → Option Operation)
    (encodeReply : Reply → ReplyWire)
    (decodeReply : ReplyWire → Option Reply) : Prop :=
  RequestCodecCorrect encodeRequest decodeRequest ∧
  ReplyCodecCorrect encodeReply decodeReply

end MovObserver.Bridge
