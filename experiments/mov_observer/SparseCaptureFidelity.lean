import WholeObserver
import Observer

namespace MovObserver.SparseCaptureFidelity
open NativeObserver WholeObserver

/-- Encode one native region as an arbitrary-sized range in the existing sparse
image model. The bound is the same nonwrapping condition checked by `makeElf`.
Bytes come from the region payload, which is the readback buffer after
`withReadback` and the target's post-state, not assumed input values. -/
def regionRange (region : Region)
    (fits : region.address.toNat + region.bytes.size ≤ 2^64) : MemoryRange where
  start := region.address.toNat
  endExclusive := region.address.toNat + region.bytes.size
  bytes := region.bytes.data.map UInt8.toBitVec
  ordered := by omega
  bounded := fits
  size_eq := by simp

/-- A single returned region is itself a finite sparse image. Arbitrary region
lengths are retained; the existing image type carries the trivial
nonoverlap proof for this one-range view. -/
def regionImage (region : Region)
    (fits : region.address.toNat + region.bytes.size ≤ 2^64) : SparseMemoryImage :=
  ⟨[regionRange region fits], by simp⟩

/-- Every returned readback byte appears at its original requested address in
the sparse-image range generated from the actual runtime helper's result. -/
theorem runtime_readback_image_fidelity (requested : Region) (readback : ByteArray)
    (lengthMatches : readback.size = requested.bytes.size)
    (fits : requested.address.toNat + readback.size ≤ 2^64)
    (i : Nat) (indexBound : i < requested.bytes.size) :
    ∃ range, range ∈ (regionImage (withReadback requested readback) fits).ranges ∧
      range.start + i = requested.address.toNat + i ∧
      i < range.bytes.size ∧
      range.bytes[i]! = (readback.data.map UInt8.toBitVec)[i]! := by
  refine ⟨regionRange (withReadback requested readback) fits, ?_, ?_, ?_, ?_⟩
  · simp [regionImage]
  · rfl
  · simp [regionRange, withReadback]
    omega
  · rfl

/-- The runtime helper used by the actual requested-range loop preserves the
requested address while replacing its bytes with the readback buffer. -/
theorem runtime_region_address_preserved (requested : Region) (readback : ByteArray) :
    (withReadback requested readback).address = requested.address :=
  withReadback_address requested readback

end MovObserver.SparseCaptureFidelity
