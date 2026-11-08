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
  | stopped (stop : StopToken) (waitStatus : UInt32) (siginfo : List (BitVec 8))
  | exited (tracee : Tracee) (waitStatus : UInt32)
  | reaped (tracee : Tracee)
  | failed (errno : UInt32) (transferred : Nat)

/-- Proposed narrow Lean effect boundary. No implementation or correctness law
is supplied. The concrete exported foreign symbol must implement this function
through the separately specified marshalling and ownership obligations. -/
structure ForeignAPI where
  invoke : Operation → IO Reply

/-- Host addresses are distinct from tracee addresses. Length uses Nat so the
ABI obligation must rule out overflow before narrowing to a machine size. -/
structure Buffer where
  base : Nat
  length : Nat
  alignment : Nat
  owner : Nat

abbrev HostMemory := Nat → BitVec 8

def BufferContains (b : Buffer) (a : Nat) : Prop :=
  b.base ≤ a ∧ a < b.base + b.length

def BufferValid (b : Buffer) : Prop :=
  0 < b.alignment ∧ b.base % b.alignment = 0 ∧
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

/-- Each buffer must stay live for the entire foreign call. Distinct owner IDs
alone do not prove disjoint storage: both properties are explicitly required. -/
def CallBuffersValid (inputs outputs : List Buffer) (liveOwners : List Nat) : Prop :=
  (∀ b ∈ inputs ++ outputs, BufferValid b ∧ b.owner ∈ liveOwners) ∧
  (∀ i ∈ inputs, ∀ o ∈ outputs, BuffersDisjoint i o) ∧
  outputs.Pairwise BuffersDisjoint

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
  returned : State → Option Reply

inductive Reaches {State : Type} (step : State → State → Prop) : State → State → Prop
  | refl (s) : Reaches step s s
  | next {a b c} : Reaches step a b → step b c → Reaches step a c

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
