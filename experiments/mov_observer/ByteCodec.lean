import Std.Tactic.BVDecide

namespace MovObserver

/-- The wire format is eight explicitly ordered, little-endian bytes. -/
def pack64 (b0 b1 b2 b3 b4 b5 b6 b7 : BitVec 8) : BitVec 64 :=
  ((((((b7 ++ b6) ++ b5) ++ b4) ++ b3) ++ b2) ++ b1) ++ b0

theorem byte_roundtrip (word : BitVec 64) :
    pack64 (BitVec.extractLsb 7 0 word) (BitVec.extractLsb 15 8 word)
      (BitVec.extractLsb 23 16 word) (BitVec.extractLsb 31 24 word)
      (BitVec.extractLsb 39 32 word) (BitVec.extractLsb 47 40 word)
      (BitVec.extractLsb 55 48 word) (BitVec.extractLsb 63 56 word) = word := by
  unfold pack64
  bv_decide

def read64 (memory : BitVec 64 → BitVec 8) (base : Nat) : BitVec 64 :=
  pack64 (memory (BitVec.ofNat 64 (base + 0)))
    (memory (BitVec.ofNat 64 (base + 1)))
    (memory (BitVec.ofNat 64 (base + 2)))
    (memory (BitVec.ofNat 64 (base + 3)))
    (memory (BitVec.ofNat 64 (base + 4)))
    (memory (BitVec.ofNat 64 (base + 5)))
    (memory (BitVec.ofNat 64 (base + 6)))
    (memory (BitVec.ofNat 64 (base + 7)))

#print axioms byte_roundtrip
end MovObserver
