import Protocol

namespace MovObserver.NativeBoundary
open Ayxg.QfAbv

/-- Raw bytes of the existing Linux AMD64 GETREGS transport, not a second
architectural state model. Field order is the Registers/FIELDS declaration in
native_probe.py. Kernel bookkeeping and unmodeled fields remain in this image. -/
abbrev RegisterImage := Fin 216 → BitVec 8

def registerWord (image : RegisterImage) (slot : Fin 27) : BitVec 64 :=
  pack64 (image ⟨slot.val * 8, by omega⟩)
    (image ⟨slot.val * 8 + 1, by omega⟩)
    (image ⟨slot.val * 8 + 2, by omega⟩)
    (image ⟨slot.val * 8 + 3, by omega⟩)
    (image ⟨slot.val * 8 + 4, by omega⟩)
    (image ⟨slot.val * 8 + 5, by omega⟩)
    (image ⟨slot.val * 8 + 6, by omega⟩)
    (image ⟨slot.val * 8 + 7, by omega⟩)

/-- Exact sixteen-GPR order already used by observeGprs/decodeRecord.
The raw transport includes orig_rax at slot 15; it is not architectural RAX. -/
def imageGprs (image : RegisterImage) : List (BitVec 64) :=
  ([10, 11, 12, 5, 19, 4, 13, 14, 9, 8, 7, 6, 3, 2, 1, 0] : List (Fin 27)).map
    (registerWord image)

/-- Partial correspondence, explicitly only the existing GPR/PC/represented
flags component. This does not discard the other raw bytes or assert that the
complete register image, FP state, segments, or memory are represented here. -/
def RegisterComponentCorresponds (image : RegisterImage) (state : Env Γ) : Prop :=
  imageGprs image = observeGprs state ∧
  registerWord image 16 = Env.lookup state v_rip ∧
  flagsFromRflags (registerWord image 18) = observeModeledFlags state

/-- The byte decoder must accept every complete image, return every byte
unchanged, and reject every wrong-length input. This is an obligation on the
future concrete Lean decoder, not an assumption about the FFI reading memory. -/
def RegisterImageDecoderCorrect
    (decode : List (BitVec 8) → Option RegisterImage) : Prop :=
  (∀ bytes, bytes.length = 216 → ∃ image, decode bytes = some image) ∧
  (∀ bytes image, decode bytes = some image →
    bytes = List.ofFn image) ∧
  (∀ bytes, bytes.length ≠ 216 → decode bytes = none)

/-- For every requested modeled register component and raw image offered for
installation, the supplied validator accepts exactly the correspondence above.
It may not replace a requested value with a subsequently observed value.
This alone says nothing about successful native installation or acquisition. -/
def RegisterRequestValidationCorrect
    (accepts : Env Γ → RegisterImage → Bool) : Prop :=
  ∀ wanted image,
    accepts wanted image = true ↔ RegisterComponentCorresponds image wanted

end MovObserver.NativeBoundary
