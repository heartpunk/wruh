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

/-- Abstract operation boundary for ordinary Lean functions and concrete FFI
calls, not a serialized dispatcher or an effect interpreter. Returned IO errors
remain errors; native syscall failures retain errno in Reply. -/
structure ForeignAPI where
  invoke : Operation → IO Reply

/-- Host addresses are distinct from tracee addresses. Length uses Nat so the
ABI obligation must rule out overflow before narrowing to a machine size. -/
structure Buffer where
  base : Nat
  length : Nat
  alignment : Nat
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

/-- Requirements on the concrete call's buffers, fixed before use rather than
inferred from the writes that happened. -/
def CallBuffersValid (inputs outputs : List Buffer) : Prop :=
  (∀ b ∈ inputs ++ outputs, BufferValid b) ∧
  (∀ i ∈ inputs, ∀ o ∈ outputs, BuffersDisjoint i o) ∧
  outputs.Pairwise BuffersDisjoint

/-- Proof relation for the actual Lean/FFI call, not an implementation interpreter.
The concrete binding supplies its steps, returned value and project-owned writes.
Buffer-frame claims concern the leaf buffer-access segment with storage supplied
by the caller; runtime allocation is outside that segment and governed by the
documented ABI contract. This is not yet a whole-call refinement proof. -/
structure Execution (State : Type) where
  initial : Operation → State
  step : State → State → Prop
  returned : State → Option (Except IO.Error Reply)
  /-- Complete ordered writes of the bound leaf buffer-access segment, including
  writes later undone. Every write in that segment must be included. Runtime
  allocation and return-object construction are outside this segment and need
  their separate documented-ABI handoff, not silent omission from its effects. -/
  writes : State → State → List (Nat × BitVec 8)

inductive Reaches {State : Type} (step : State → State → Prop) : State → State → Prop
  | refl (s) : Reaches step s s
  | next {a b c} : Reaches step a b → step b c → Reaches step a c

/-- Borrowed storage remains valid throughout the call. `live` must be bound
to the concrete function's documented ABI lifetime, not a new allocator model.
Our handoff must satisfy that ABI contract; runtime correctness is not re-proved. -/
def CallBufferLifetime {State : Type} (e : Execution State)
    (live : State → Buffer → Prop) (request : Operation) (buffers : List Buffer) : Prop :=
  ∀ s, Reaches e.step (e.initial request) s →
    ∀ b ∈ buffers, BufferValid b ∧ live s b

/-- Project-owned writes stay inside the concrete function's output/scratch
buffers, and borrowed input bytes stay unchanged, including failed prefixes.
Output/scratch storage must be valid and live before use. Runtime allocation
internals are governed by the imported ABI contract, not enumerated here.
`memory` and `e.writes` describe the same actual call; complete project-owned
writes must be supplied by its binding, not selected to make this claim true. -/
def CallDynamicMemoryFrame {State : Type} (e : Execution State)
    (memory : State → HostMemory) (live : State → Buffer → Prop)
    (request : Operation) (inputs : List Buffer)
    (outputs scratch : State → List Buffer) : Prop :=
  CallBufferLifetime e live request inputs ∧
  ∀ s, Reaches e.step (e.initial request) s →
    CallBuffersValid inputs (outputs s ++ scratch s) ∧
    (∀ b ∈ outputs s ++ scratch s, live s b) ∧
    (∀ b ∈ inputs, ∀ a, BufferContains b a →
      memory s a = memory (e.initial request) a) ∧
    (∀ next, e.step s next →
      HostFrame (outputs s ++ scratch s) (memory s) (memory next) ∧
      ∀ write ∈ e.writes s next,
        (∃ b ∈ outputs s ++ scratch s, BufferContains b write.1) ∧
        (∀ b ∈ inputs, ¬ BufferContains b write.1))

/-- Preallocated-output instance of the same concrete-call frame. -/
def CallMemoryFrame {State : Type} (e : Execution State)
    (memory : State → HostMemory) (live : State → Buffer → Prop)
    (request : Operation) (inputs outputs : List Buffer)
    (scratch : State → List Buffer) : Prop :=
  CallDynamicMemoryFrame e memory live request inputs (fun _ => outputs) scratch

/-- No infinite path, stuck nonterminal state, or execution past return.
This is intentionally stronger than existence of one terminating execution.
For nonexceptional runs, external primitive progress and target termination
are premises of the future instantiated theorem; termination of project-owned
code is an obligation, not an imported premise. -/
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
    e.returned state = some (.ok reply) → OperationReplyCompatible request reply

/-- Interface-wide claim retained separately from an admitted individual call. -/
def CallReplyCompatible {State : Type} (e : Execution State) : Prop :=
  ∀ request, CallReplyCompatibleFor e request

end MovObserver.Bridge
