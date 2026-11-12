import Hegel
import Lean
import Observer

/-! Catalogue-backed generated inputs for the native instruction PBT. -/
namespace Wruh.IFormPbt

open Lean Hegel

structure Occurrence where
  iform : String
  bytes : ByteArray
  targetId : String
  binarySha256 : String
  functionId : String
  address : Nat
  occurrenceId : Nat
  deriving Inhabited

structure GeneratedCase where
  occurrence : Occurrence
  gprs : Array UInt64
  flags : UInt64
  memoryAddress : UInt64
  memoryBytes : ByteArray
  deriving Inhabited

private def hexDigit (c : Char) : Except String Nat :=
  if '0' ≤ c && c ≤ '9' then pure (c.toNat - '0'.toNat)
  else if 'a' ≤ c && c ≤ 'f' then pure (10 + c.toNat - 'a'.toNat)
  else if 'A' ≤ c && c ≤ 'F' then pure (10 + c.toNat - 'A'.toNat)
  else throw s!"invalid hex digit {c}"

private def decodeHex (text : String) : Except String ByteArray := do
  let chars := text.toList.toArray
  if chars.isEmpty || chars.size % 2 != 0 then throw "instruction bytes must be nonempty even-length hex"
  let mut bytes := ByteArray.empty
  for i in [:chars.size / 2] do
    let hi ← hexDigit chars[2*i]!
    let lo ← hexDigit chars[2*i+1]!
    bytes := bytes.push (UInt8.ofNat (hi * 16 + lo))
  pure bytes

private def field (json : Json) (name : String) : Except String Json := json.getObjVal? name

private def parseOccurrence (row item : Json) : Except String Occurrence := do
  let iform ← (← field row "iform").getStr?
  let bytes ← decodeHex (← (← field row "bytes").getStr?)
  let targetId ← (← field item "target_id").getStr?
  let binarySha256 ← (← field item "binary_sha256").getStr?
  let functionId ← (← field item "function_id").getStr?
  let address ← (← field item "address").getNat?
  let occurrenceId ← (← field item "occurrence_id").getNat?
  pure ⟨iform, bytes, targetId, binarySha256, functionId, address, occurrenceId⟩

def readCatalogue (path : System.FilePath) : IO (Array Occurrence) := do
  let contents ← IO.FS.readFile path
  let mut occurrences := #[]
  for line in contents.splitOn "\n" do
    if !line.trimAscii.toString.isEmpty then
      let row ← match Json.parse line with
        | .ok value => pure value
        | .error error => throw <| IO.userError s!"catalogue row: {error}"
      let items ← match field row "occurrences" with
        | .ok value => match value.getArr? with
          | .ok array => pure array
          | .error error => throw <| IO.userError s!"catalogue row: {error}"
        | .error error => throw <| IO.userError s!"catalogue row: {error}"
      for item in items do
        match parseOccurrence row item with
        | .ok occurrence => occurrences := occurrences.push occurrence
        | .error error => throw <| IO.userError s!"catalogue row: {error}"
  if occurrences.isEmpty then throw <| IO.userError "instruction catalogue has no occurrences"
  pure occurrences

private def chooseUInt64 : Generator NativeGen UInt64 := ⟨do
  let hi ← DataSource.chooseNat 0 0xffffffff
  let lo ← DataSource.chooseNat 0 0xffffffff
  pure <| UInt64.ofNat (hi * 0x100000000 + lo)⟩

private def chooseMemory : Generator NativeGen ByteArray :=
  Generator.bytes 1024 1024

private def chooseGprs : Generator NativeGen (Array UInt64) := ⟨do
  let mut registers := #[]
  for _ in [:16] do
    let pointer ← DataSource.chooseBool
    let value ← if pointer then do
      pure (UInt64.ofNat (0x100000000 + (← DataSource.chooseNat 0 1015)))
    else chooseUInt64.generate
    registers := registers.push value
  -- The observer fixture supplies this mapped page for stack operations.
  registers := registers.set! 4 (0x100000000 + 1024 - 16)
  pure registers⟩

private def chooseFlags : Generator NativeGen UInt64 := ⟨do
  let bits ← DataSource.chooseNat 0 63
  let positions : Array Nat := #[0,2,4,6,7,11]
  let mut flags : UInt64 := 0x202
  for i in [:6] do
    if bits / (2^i) % 2 == 1 then
      flags := flags ||| (UInt64.ofNat 1 <<< UInt64.ofNat positions[i]!)
  pure flags⟩

def generatedState (occurrence : Occurrence) : Generator NativeGen GeneratedCase := ⟨do
  let gprs ← chooseGprs.generate
  let flags ← chooseFlags.generate
  let memoryBytes ← chooseMemory.generate
  pure {
    occurrence
    gprs
    flags
    memoryAddress := 0x100000000
    memoryBytes
  }⟩

def generatedCase (catalogue : Array Occurrence) : Generator NativeGen GeneratedCase := ⟨do
  if catalogue.isEmpty then throw <| IO.userError "cannot sample an empty instruction catalogue"
  let index ← DataSource.chooseNat 0 (catalogue.size - 1)
  let some occurrence := catalogue[index]? | throw <| IO.userError "catalogue occurrence index out of range"
  (generatedState occurrence).generate⟩

/-- Supply the generated instruction and concrete initial state to the native observer. -/
def GeneratedCase.observerRequest (c : GeneratedCase) : MovObserver.NativeObserver.Request :=
  { instruction := c.occurrence.bytes
    gprs := c.gprs
    flags := c.flags
    memory := #[{ address := c.memoryAddress, bytes := c.memoryBytes }] }

end Wruh.IFormPbt
