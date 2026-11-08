import VectorProtocol

namespace MovObserver.LegacyFp
open Ayxg.QfAbv

/-- Exact evidence returned by the existing getfp calibration operation.
All padding, reserved bytes and capability metadata remain present. This is
not the full extended-state image and does not contain upper YMM/ZMM or masks. -/
abbrev Image := Fin 512 → BitVec 8

/-- Little-endian field extraction used solely to define the wire relation. -/
def littleEndian (width base count : Nat) (image : Image) : BitVec width :=
  BitVec.ofNat width ((List.range count).foldl
    (fun acc i => acc + (if h : base + i < 512 then
      (image ⟨base + i, h⟩).toNat * 2^(8*i) else 0)) 0)

/-- Raw field encodings, not floating-point numerical values. The tag here is
abridged, not the full x87 tag word. Reserved bits in control/status/opcode fields
are retained. No numerical conversion or NaN/payload normalization is permitted. -/
structure Fields where
  control : BitVec 16
  status : BitVec 16
  abridgedTag : BitVec 8
  opcodeWord : BitVec 16
  instructionPointer : BitVec 64
  dataPointer : BitVec 64
  mxcsr : BitVec 32
  mxcsrMask : BitVec 32
  slots : Fin 8 → BitVec 80
  xmm : Fin 16 → BitVec 128

/-- Byte layout of the 64-bit legacy FP image used by the current probe.
The saved slots are identified by image position here; conversion between
logical ST(i), physical registers and TOP is not silently assumed. -/
def FieldsMatch (image : Image) (f : Fields) : Prop :=
  f.control = littleEndian 16 0 2 image ∧
  f.status = littleEndian 16 2 2 image ∧
  f.abridgedTag = littleEndian 8 4 1 image ∧
  f.opcodeWord = littleEndian 16 6 2 image ∧
  f.instructionPointer = littleEndian 64 8 8 image ∧
  f.dataPointer = littleEndian 64 16 8 image ∧
  f.mxcsr = littleEndian 32 24 4 image ∧
  f.mxcsrMask = littleEndian 32 28 4 image ∧
  (∀ i, f.slots i = littleEndian 80 (32 + 16*i.val) 10 image) ∧
  (∀ i, f.xmm i = littleEndian 128 (160 + 16*i.val) 16 image)

/-- Raw evidence is returned alongside interpretation so bytes outside these
fields cannot disappear. MXCSR_MASK is capability metadata, not mutable state. -/
structure Decoded where
  raw : Image
  fields : Fields

def DecoderCorrect (decode : List (BitVec 8) → Option Decoded) : Prop :=
  (∀ bytes, bytes.length = 512 → ∃ result, decode bytes = some result) ∧
  (∀ bytes result, decode bytes = some result →
    bytes = List.ofFn result.raw ∧ FieldsMatch result.raw result.fields) ∧
  (∀ bytes, bytes.length ≠ 512 → decode bytes = none)

/-- Only the captured low 128 bits of the first sixteen modeled ZMM fields.
This is neither upper-vector coverage nor an x87 representation claim. -/
def XmmCorresponds (f : Fields) (state : Env Γ) : Prop :=
  ∀ i : Fin 16,
    f.xmm i = BitVec.extractLsb 127 0
      (Env.lookup state (VectorProtocol.zmmVar ⟨i.val, by omega⟩))

/-- The actual modeled FP fields, kept separate from the raw 80-bit slot format.
Their native conversion is still an explicit specification gap. In particular,
eight raw 80-bit payloads cannot simply be renamed as this 512-bit backing field. -/
structure ModeledFp where
  registers : BitVec 512
  tags : BitVec 64
  top : BitVec 32
  rounding : BitVec 64
  condition : BitVec 64
  sseRounding : BitVec 64

def observeModeledFp (state : Env Γ) : ModeledFp :=
  ⟨Env.lookup state v_fpreg, Env.lookup state v_fptag,
   Env.lookup state v_ftop, Env.lookup state v_fpround,
   Env.lookup state v_fc3210, Env.lookup state v_sseround⟩

end MovObserver.LegacyFp
