import Observer

namespace Wruh.IFormPbt

open MovObserver.NativeObserver

def isVectorField (name : String) : Bool :=
  name == "sseround" ||
    (name.startsWith "zmm" && ((name.drop 3).toString.toNat?.map (fun n => decide (n < 32))).getD false) ||
    (name.startsWith "k" && ((name.drop 1).toString.toNat?.map (fun n => decide (n < 8))).getD false)

private def littleEndian (bytes : ByteArray) (offset length : Nat) : Except String Nat := do
  if offset + length > bytes.size then throw "truncated native vector state"
  let mut result := 0
  for i in [:length] do result := result + bytes[offset+i]!.toNat * 2^(8*i)
  pure result

private def component (layout : VectorLayout) (bytes : ByteArray)
    (bit offset length : Nat) : Except String Nat := do
  if (layout.enabled.toNat / 2^bit) % 2 == 0 || (word bytes 512).toNat / 2^bit % 2 == 0 then
    return 0
  littleEndian bytes offset length

/-- Decode the vector and rounding fields exposed by the existing observer. -/
def nativeVectorField (name : String) (layout : Option VectorLayout)
    (fp : ByteArray) (xstate : Option ByteArray) : Except String (Option Nat) := do
  if name == "sseround" then
    let value ← littleEndian fp 24 4
    return some ((value / 2^13) % 4)
  if name.startsWith "zmm" then
    let some register := (name.drop 3).toString.toNat? | return none
    if register ≥ 32 then return none
    if register < 16 then
      let low ← match layout, xstate with
        | some l, some bytes => component l bytes 1 (160+register*16) 16
        | _, _ => littleEndian fp (160+register*16) 16
      let (middle, high) ← match layout, xstate with
        | some l, some bytes => do
            pure (← component l bytes 2 (l.ymm+register*16) 16,
                  ← component l bytes 6 (l.zmmHi+register*32) 32)
        | _, _ => pure (0, 0)
      return some (low + middle * 2^128 + high * 2^256)
    else
      match layout, xstate with
      | some l, some bytes => return some (← component l bytes 7 (l.hi16+(register-16)*64) 64)
      | _, _ => return some 0
  if name.startsWith "k" then
    let some register := (name.drop 1).toString.toNat? | return none
    if register ≥ 8 then return none
    match layout, xstate with
    | some l, some bytes => return some (← component l bytes 5 (l.masks+register*8) 8)
    | _, _ => return some 0
  pure none

end Wruh.IFormPbt
