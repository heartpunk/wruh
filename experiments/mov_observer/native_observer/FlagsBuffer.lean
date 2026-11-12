import Init

namespace MovObserver.NativeObserver

-- Shared unchanged little-endian transport algorithms used by the observer.
def word (b : ByteArray) (offset : Nat) : UInt64 := Id.run do
  let mut v : UInt64 := 0
  for i in [:8] do v := v ||| ((b[offset+i]!).toUInt64 <<< UInt64.ofNat (8*i))
  return v
def putWord (b : ByteArray) (offset : Nat) (v : UInt64) : ByteArray := Id.run do
  let mut b := b
  for i in [:8] do b := b.set! (offset+i) (v >>> UInt64.ofNat (8*i)).toUInt8
  return b

/-- RFLAGS slot in Linux x86-64 user_regs_struct. -/
def writeFlagsWord (buffer : ByteArray) (flags : UInt64) : ByteArray :=
  putWord buffer (18 * 8) flags

def readFlagsWord (buffer : ByteArray) : UInt64 :=
  word buffer (18 * 8)

end MovObserver.NativeObserver
