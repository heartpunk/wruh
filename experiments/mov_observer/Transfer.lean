import Bridge

namespace MovObserver.Bridge
open Ayxg.QfAbv
open NativeBoundary

/-- Native transport evidence for one stopped process. This is raw acquisition
state, not a replacement architectural semantics. Unmapped memory remains absent.
`none` means unmapped, not merely inaccessible through a particular read API.
The execution binding must obtain it from that process, not model predictions. -/
structure StoppedMemory where
  stop : StopToken
  registers : RegisterImage
  memory : BitVec 64 → Option (BitVec 8)

/-- Wherever a native byte exists, its value corresponds to the existing AYXG
memory field. This relation does not claim the model's total array records
native mapping/permissions, or permit inventing bytes for absent addresses. -/
def MemoryCorresponds (native : StoppedMemory) (modeled : Env Γ) : Prop :=
  ∀ address byte, native.memory address = some byte →
    Env.lookup modeled v_mem address = byte

def AddressRangeValid (base : BitVec 64) (length : Nat) : Prop :=
  base.toNat + length ≤ 2^64

def ByteAddress (base : BitVec 64) (offset : Nat) : BitVec 64 :=
  BitVec.ofNat 64 (base.toNat + offset)

/-- Complete read prefix, including a prefix obtained before an error. -/
def ReadPrefix (before : StoppedMemory) (base : BitVec 64)
    (bytes : List (BitVec 8)) : Prop :=
  AddressRangeValid base bytes.length ∧
  ∀ i : Fin bytes.length, before.memory (ByteAddress base i.val) = some bytes[i]

/-- The bridge must preserve this internal receipt even when returning failure.
The public reply alone does not carry the prefix or native write events. These
are evidence, not inferred from the requested payload or final memory. -/
structure TransferReceipt where
  before : StoppedMemory
  after : StoppedMemory
  reply : Reply
  readPrefix : List (BitVec 8)
  writes : List (BitVec 64 × BitVec 8)

/-- Reading a stopped tracee has no native writes, changes neither memory nor
registers, and does not resume it. A success is complete; a failure retains the
exact prefix and its length. Error causality is a separate kernel/ABI obligation. -/
def MemoryReadCorrect (stop : StopToken) (base : BitVec 64) (length : Nat)
    (r : TransferReceipt) : Prop :=
  r.before.stop = stop ∧ r.after.stop = stop ∧
  r.after.registers = r.before.registers ∧ r.after.memory = r.before.memory ∧
  r.writes = [] ∧ r.readPrefix.length ≤ length ∧ ReadPrefix r.before base r.readPrefix ∧
  match r.reply with
  | .bytes returned bytes =>
      returned = stop ∧ bytes = r.readPrefix ∧ bytes.length = length
  | .failed _ transferred => transferred = r.readPrefix.length
  | _ => False

/-- Logical completed prefix and endpoint preservation. This deliberately does
not prescribe byte order or number of physical writes. Actual touches require
NativeWriteFootprint below; wider read/modify/write effects require a separate
noninterference justification, not an inference from equal endpoint values. -/
def WrittenPrefix (base : BitVec 64) (bytes : List (BitVec 8)) (count : Nat)
    (r : TransferReceipt) : Prop :=
  count ≤ bytes.length ∧ AddressRangeValid base count ∧
  (∀ i : Fin count,
    r.before.memory (ByteAddress base i.val) ≠ none ∧
    r.after.memory (ByteAddress base i.val) = bytes[i.val]?) ∧
  (∀ address, (∀ i : Fin count, address ≠ ByteAddress base i.val) →
    r.after.memory address = r.before.memory address)

/-- Fixed declared native touch footprint, not inferred after execution. This
only bounds events; it does not establish that repeated/equal-value writes to
shared or device-backed memory are noninterfering. That remains an explicit
profile/environment obligation of the whole observer. -/
def NativeWriteFootprint (allowedTouches : List (BitVec 64))
    (r : TransferReceipt) : Prop :=
  ∀ write ∈ r.writes, write.1 ∈ allowedTouches

def MemoryWriteCorrect (stop : StopToken) (base : BitVec 64)
    (bytes : List (BitVec 8)) (allowedTouches : List (BitVec 64))
    (r : TransferReceipt) : Prop :=
  NativeWriteFootprint allowedTouches r ∧
  r.before.stop = stop ∧ r.after.stop = stop ∧
  r.after.registers = r.before.registers ∧ r.readPrefix = [] ∧
  match r.reply with
  | .written returned count =>
      returned = stop ∧ count = bytes.length ∧ WrittenPrefix base bytes count r
  | .failed _ count => WrittenPrefix base bytes count r
  | _ => False

/-- All actual transfer outcomes must satisfy the operation-specific relation;
Snapshots here require a stable-memory environment for the call interval;
a StopToken alone does not establish that premise (shared writers may exist).
The complete contract must either establish stability from containment or model
interference. Neither choice is asserted by this safety component.
A transfer implementation must also discharge availability and finite execution
in the complete bridge contract. This safety component alone permits fail-all. -/
def MemoryTransferSafety
    (runs : Operation → TransferReceipt → Prop)
    (writeFootprint : StopToken → BitVec 64 → List (BitVec 8) → List (BitVec 64)) : Prop :=
  (∀ stop base length r, runs (.readMemory stop base length) r →
    MemoryReadCorrect stop base length r) ∧
  (∀ stop base bytes r, runs (.writeMemory stop base bytes) r →
    MemoryWriteCorrect stop base bytes (writeFootprint stop base bytes) r)

end MovObserver.Bridge
