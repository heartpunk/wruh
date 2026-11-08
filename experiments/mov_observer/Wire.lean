import Bridge

namespace MovObserver.Wire
open Bridge

/-- Proposed sole foreign entry signature: a borrowed request byte array and an
owned IO-result byte array. The future extern declaration must use @& on its
request argument; this type alias alone does not impose runtime borrowing.
No foreign symbol or implementation is declared here. -/
abbrev ForeignCall := ByteArray → IO ByteArray

def symbol : String := "wruh_observer_call_v1"

/-- Seven 64-bit little-endian words followed by a 64-bit payload length and
payload bytes. Explicit fixed layout avoids passing Lean ADT internals across
the project-owned bridge. The Lean ByteArray/IO ABI still needs its runtime proof. -/
structure Frame where
  words : List Nat
  payload : List (BitVec 8)

def LE64 (word : Nat) : List (BitVec 8) :=
  (List.range 8).map fun i => BitVec.ofNat 8 (word / 2^(8*i))

def FrameFits (f : Frame) : Prop :=
  f.words.length = 7 ∧ (∀ word ∈ f.words, word < 2^64) ∧ 64 + f.payload.length < 2^64

def FrameMatches (f : Frame) (bytes : ByteArray) : Prop :=
  FrameFits f ∧ bytes.data.toList.map (fun b => b.toBitVec) =
    f.words.flatMap LE64 ++ LE64 f.payload.length ++ f.payload

/-- Operation tags are project wire tags, NOT Linux ptrace request numbers.
Slots: tag, pid, generation, stop serial, address, requested length, reserved.
Process/stop generations therefore cannot be lost during serialization. -/
def RequestFrame : Operation → Frame
  | .create => ⟨[0,0,0,0,0,0,0], []⟩
  | .readRegisters s => ⟨[1,s.tracee.pid.toNat,s.tracee.generation,s.serial,0,216,0], []⟩
  | .writeRegisters s bytes =>
      ⟨[2,s.tracee.pid.toNat,s.tracee.generation,s.serial,0,bytes.length,0], bytes⟩
  | .readMemory s address length =>
      ⟨[3,s.tracee.pid.toNat,s.tracee.generation,s.serial,address.toNat,length,0], []⟩
  | .writeMemory s address bytes =>
      ⟨[4,s.tracee.pid.toNat,s.tracee.generation,s.serial,address.toNat,bytes.length,0], bytes⟩
  | .singleStep s => ⟨[5,s.tracee.pid.toNat,s.tracee.generation,s.serial,0,0,0], []⟩
  | .wait t => ⟨[6,t.pid.toNat,t.generation,0,0,0,0], []⟩
  | .reap t => ⟨[7,t.pid.toNat,t.generation,0,0,0,0], []⟩

/-- Reply slots: tag, pid, generation, stop serial, errno/wait status, count,
siginfo-present. An absent siginfo differs from a present empty byte payload. -/
def ReplyFrame : Reply → Frame
  | .created t => ⟨[0,t.pid.toNat,t.generation,0,0,0,0], []⟩
  | .bytes s bytes =>
      ⟨[1,s.tracee.pid.toNat,s.tracee.generation,s.serial,0,bytes.length,0], bytes⟩
  | .written s count => ⟨[2,s.tracee.pid.toNat,s.tracee.generation,s.serial,0,count,0], []⟩
  | .resumed s => ⟨[3,s.tracee.pid.toNat,s.tracee.generation,s.serial,0,0,0], []⟩
  | .stopped s status none =>
      ⟨[4,s.tracee.pid.toNat,s.tracee.generation,s.serial,status.toNat,0,0], []⟩
  | .stopped s status (some bytes) =>
      ⟨[4,s.tracee.pid.toNat,s.tracee.generation,s.serial,status.toNat,0,1], bytes⟩
  | .exited t status => ⟨[5,t.pid.toNat,t.generation,0,status.toNat,0,0], []⟩
  | .reaped t => ⟨[6,t.pid.toNat,t.generation,0,0,0,0], []⟩
  | .failed errno transferred => ⟨[7,0,0,0,errno.toNat,transferred,0], []⟩

/-- Header-plus-payload arithmetic must be checked before allocating or indexing.
The bound below is wire addressability, not an assumption that allocation succeeds;
actual runtime size/resource limits and their errors remain bridge obligations.
Exact encoding, including rejection rather than truncation of unbounded
Nat metadata. The closed frame equations above are the independent specification. -/
def RequestEncoderCorrect (encode : Operation → Option ByteArray) : Prop :=
  (∀ request, FrameFits (RequestFrame request) → ∃ bytes, encode request = some bytes) ∧
  (∀ request bytes, encode request = some bytes → FrameMatches (RequestFrame request) bytes) ∧
  (∀ request, ¬ FrameFits (RequestFrame request) → encode request = none)

/-- A decoder accepts exactly complete canonical frames. This rejects unknown
tags, reserved bits/words, inconsistent lengths, trailing bytes and overflow;
no mere round-trip agreement between two potentially incorrect codecs suffices. -/
def ReplyDecoderCorrect (decode : ByteArray → Option Reply) : Prop :=
  (∀ bytes reply, decode bytes = some reply ↔ FrameMatches (ReplyFrame reply) bytes) ∧
  (∀ bytes, (¬ ∃ reply, FrameMatches (ReplyFrame reply) bytes) → decode bytes = none)

/-- Bidirectional foreign-side obligations for the same closed wire format. -/
def RequestDecoderCorrect (decode : ByteArray → Option Operation) : Prop :=
  (∀ bytes request, decode bytes = some request ↔ FrameMatches (RequestFrame request) bytes) ∧
  (∀ bytes, (¬ ∃ request, FrameMatches (RequestFrame request) bytes) → decode bytes = none)

def ReplyEncoderCorrect (encode : Reply → Option ByteArray) : Prop :=
  (∀ reply, FrameFits (ReplyFrame reply) → ∃ bytes, encode reply = some bytes) ∧
  (∀ reply bytes, encode reply = some bytes → FrameMatches (ReplyFrame reply) bytes) ∧
  (∀ reply, ¬ FrameFits (ReplyFrame reply) → encode reply = none)

/-- The runtime error branch is not an encoded native errno reply. Malformed
successful wire returns retain their exact bytes as a distinct boundary failure. -/
abbrev DecodedReturn := Except IO.Error DecodedReply

/-- Fixed independent relation for ALL returned IO outcomes. It neither turns
runtime errors into native replies nor assumes every successful byte-array return
is a well-formed reply. Runtime aborts are not returned IO outcomes. -/
def ForeignReturnMatches : Except IO.Error ByteArray → DecodedReturn → Prop
  | .ok bytes, .ok (.reply value) => FrameMatches (ReplyFrame value) bytes
  | .ok bytes, .ok (.malformed retained) =>
      retained = bytes ∧ ¬ ∃ value, FrameMatches (ReplyFrame value) bytes
  | .error error, .error retained => retained = error
  | _, _ => False

def ForeignReturnDecoderCorrect
    (decode : Except IO.Error ByteArray → DecodedReturn) : Prop :=
  ∀ raw result, decode raw = result ↔ ForeignReturnMatches raw result

end MovObserver.Wire
