import FlagsConversion
import InstallationFidelity
import FlagsBuffer

set_option maxRecDepth 16384
set_option maxHeartbeats 2000000

namespace MovObserver.NativeObserver

private theorem putWord_unroll (b : ByteArray) (offset : Nat) (v : UInt64) :
    putWord b offset v =
      ((((((((b.set! (offset + 0) (v >>> 0).toUInt8).set! (offset + 1) (v >>> 8).toUInt8).set! (offset + 2) (v >>> 16).toUInt8).set! (offset + 3) (v >>> 24).toUInt8).set! (offset + 4) (v >>> 32).toUInt8).set! (offset + 5) (v >>> 40).toUInt8).set! (offset + 6) (v >>> 48).toUInt8).set! (offset + 7) (v >>> 56).toUInt8) := by
  simp [putWord, List.range']

private theorem word_unroll (b : ByteArray) (offset : Nat) :
    word b offset =
      (((((((((0 : UInt64) ||| (b[offset + 0]!.toUInt64 <<< 0)) ||| (b[offset + 1]!.toUInt64 <<< 8)) ||| (b[offset + 2]!.toUInt64 <<< 16)) ||| (b[offset + 3]!.toUInt64 <<< 24)) ||| (b[offset + 4]!.toUInt64 <<< 32)) ||| (b[offset + 5]!.toUInt64 <<< 40)) ||| (b[offset + 6]!.toUInt64 <<< 48)) ||| (b[offset + 7]!.toUInt64 <<< 56)) := by
  simp [word, List.range']

theorem writeFlagsWord_size (b : ByteArray) (v : UInt64) :
    (writeFlagsWord b v).size = b.size := by
  simp [writeFlagsWord, putWord_unroll]

theorem writeFlagsWord_frame (b : ByteArray) (v : UInt64) (i : Nat)
    (outside : i < 144 ∨ 152 ≤ i) :
    (writeFlagsWord b v)[i]! = b[i]! := by
  simp only [writeFlagsWord, putWord_unroll]
  simp (disch := omega) only [ByteArray.getElem!_set!_ne]

theorem writeFlagsWord_byte (b : ByteArray) (v : UInt64)
    (size : 152 ≤ b.size) (i : Fin 8) :
    (writeFlagsWord b v)[144 + i.val]! = (v >>> UInt64.ofNat (8 * i.val)).toUInt8 := by
  have cases_i : i.val = 0 ∨ i.val = 1 ∨ i.val = 2 ∨ i.val = 3 ∨
      i.val = 4 ∨ i.val = 5 ∨ i.val = 6 ∨ i.val = 7 := by omega
  rcases cases_i with hi | hi | hi | hi | hi | hi | hi | hi <;>
    simp (disch := simp only [ByteArray.size_set!]; omega) only
      [writeFlagsWord, putWord_unroll, hi, ByteArray.getElem!_set!,
        Nat.reduceMul, Nat.reduceAdd, ↓reduceIte] <;>
    first | rfl | simpa using (ByteArray.getElem!_set!_self b 144 (v >>> 0).toUInt8 (by omega))

private theorem nativePack (b0 b1 b2 b3 b4 b5 b6 b7 : UInt8) :
    (((((((((0 : UInt64) ||| (b0.toUInt64 <<< 0)) ||| (b1.toUInt64 <<< 8)) ||| (b2.toUInt64 <<< 16)) ||| (b3.toUInt64 <<< 24)) ||| (b4.toUInt64 <<< 32)) ||| (b5.toUInt64 <<< 40)) ||| (b6.toUInt64 <<< 48)) ||| (b7.toUInt64 <<< 56)).toBitVec =
    pack64 b0.toBitVec b1.toBitVec b2.toBitVec b3.toBitVec
      b4.toBitVec b5.toBitVec b6.toBitVec b7.toBitVec := by
  simp only [UInt64.toBitVec_or, UInt64.toBitVec_shiftLeft, UInt8.toBitVec_toUInt64]
  change (((((((((0 : BitVec 64) ||| (b0.toBitVec.setWidth 64 <<< (0 : Nat))) ||| (b1.toBitVec.setWidth 64 <<< (8 : Nat))) ||| (b2.toBitVec.setWidth 64 <<< (16 : Nat))) ||| (b3.toBitVec.setWidth 64 <<< (24 : Nat))) ||| (b4.toBitVec.setWidth 64 <<< (32 : Nat))) ||| (b5.toBitVec.setWidth 64 <<< (40 : Nat))) ||| (b6.toBitVec.setWidth 64 <<< (48 : Nat))) ||| (b7.toBitVec.setWidth 64 <<< (56 : Nat))) = _
  apply BitVec.eq_of_getLsbD_eq
  intro i hi
  simp only [pack64, BitVec.getLsbD_append, BitVec.getLsbD_or,
    BitVec.getLsbD_shiftLeft, BitVec.getLsbD_setWidth]
  grind

theorem read_writeFlagsWord (b : ByteArray) (v : UInt64) (size : 152 ≤ b.size) :
    readFlagsWord (writeFlagsWord b v) = v := by
  apply UInt64.toBitVec_inj.mp
  rw [readFlagsWord, word_unroll]
  rw [writeFlagsWord_byte b v size ⟨0, by decide⟩]
  rw [writeFlagsWord_byte b v size ⟨1, by decide⟩]
  rw [writeFlagsWord_byte b v size ⟨2, by decide⟩]
  rw [writeFlagsWord_byte b v size ⟨3, by decide⟩]
  rw [writeFlagsWord_byte b v size ⟨4, by decide⟩]
  rw [writeFlagsWord_byte b v size ⟨5, by decide⟩]
  rw [writeFlagsWord_byte b v size ⟨6, by decide⟩]
  rw [writeFlagsWord_byte b v size ⟨7, by decide⟩]
  rw [nativePack]
  exact nativeByteRoundtrip v

/-- Interpret the concrete transport word through the existing modeled codec. -/
def decodeFlagsBuffer (buffer : ByteArray) : ModeledFlags :=
  flagsFromRflags (readFlagsWord buffer).toBitVec

theorem decode_writeFlagsWord (b : ByteArray) (v : UInt64) (size : 152 ≤ b.size) :
    decodeFlagsBuffer (writeFlagsWord b v) = flagsFromRflags v.toBitVec := by
  simp only [decodeFlagsBuffer, read_writeFlagsWord b v size]

theorem flags_buffer_fidelity (b : ByteArray) (size : 152 ≤ b.size)
    (f : ModeledFlags) (valid : f.Valid) :
    ∃ encoded : BitVec 64,
      flagsToRflags f (readFlagsWord b).toBitVec = some encoded ∧
      decodeFlagsBuffer (writeFlagsWord b (UInt64.ofBitVec encoded)) = f ∧
      (writeFlagsWord b (UInt64.ofBitVec encoded)).size = b.size ∧
      (∀ i : Nat, i < 144 ∨ 152 ≤ i →
        (writeFlagsWord b (UInt64.ofBitVec encoded))[i]! = b[i]!) ∧
      (encoded &&& ~~~modeledRflagsMask) =
        ((readFlagsWord b).toBitVec &&& ~~~modeledRflagsMask) := by
  obtain ⟨encoded, encode, decode, frame⟩ :=
    flags_conversion_correct.2.1 f (readFlagsWord b).toBitVec valid
  refine ⟨encoded, encode, ?_, writeFlagsWord_size _ _, ?_, frame⟩
  · rw [decode_writeFlagsWord b (UInt64.ofBitVec encoded) size]
    exact decode
  · exact fun i outside => writeFlagsWord_frame b (UInt64.ofBitVec encoded) i outside

#print axioms writeFlagsWord_size
#print axioms writeFlagsWord_frame
#print axioms read_writeFlagsWord
#print axioms flags_buffer_fidelity

end MovObserver.NativeObserver
