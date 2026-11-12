import Init

namespace MovObserver.NativeObserver

/-- The exact native input record: sixteen requested 64-bit GPRs, in the
existing loader order, serialized into all 128 little-endian bytes.
The caller's existing sixteen-register validation is unchanged. -/
def encodeGprs (gprs : Array UInt64) : ByteArray :=
  ByteArray.mk (Array.ofFn fun i : Fin 128 =>
    (gprs[i.val / 8]! >>> UInt64.ofNat (8 * (i.val % 8))).toUInt8)

end MovObserver.NativeObserver
