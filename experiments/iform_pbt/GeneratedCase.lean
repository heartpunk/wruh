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
  vectorSeed : ByteArray
  sseRounding : UInt64
  deriving Inhabited

structure StateIdentity where
  gprs : Array UInt64
  flags : UInt64
  memoryAddress : UInt64
  memoryBytes : ByteArray
  vectorSeed : ByteArray
  sseRounding : UInt64
  deriving BEq

def GeneratedCase.stateIdentity (c : GeneratedCase) : StateIdentity :=
  ⟨c.gprs, c.flags, c.memoryAddress, c.memoryBytes, c.vectorSeed, c.sseRounding⟩

-- SplitMix64 supplies reproducible shuffle choices independently of Hegel's
-- deliberate boundary-value exploration. Rejection avoids modulo bias.
private def nextRandom (state : UInt64) : UInt64 × UInt64 := Id.run do
  let state := state + 0x9e3779b97f4a7c15
  let mut z := state
  z := (z ^^^ (z >>> 30)) * 0xbf58476d1ce4e5b9
  z := (z ^^^ (z >>> 27)) * 0x94d049bb133111eb
  return (state, z ^^^ (z >>> 31))

def sampleOccurrences (catalogue : Array Occurrence) (budget : Nat)
    (seed : UInt64) : Array Occurrence := Id.run do
  let mut result := catalogue
  let mut state := seed
  for i in [:min budget result.size] do
    let bound := UInt64.ofNat (result.size - i)
    let threshold := (0 - bound) % bound
    let mut draw : UInt64 := 0
    let mut ready := false
    while !ready do
      let (next, value) := nextRandom state
      state := next
      draw := value
      ready := draw ≥ threshold
    let j := i + (draw % bound).toNat
    let first := result[i]!
    result := result.set! i result[j]!
    result := result.set! j first
  return result.extract 0 (min budget result.size)

structure SimpleAddress where
  base : Nat
  displacement : UInt64
  width : Nat
  deriving Inhabited

theorem generatedOffsetInImage (n width : Nat) (h : width ≤ 1024) :
    (n % (1025 - width) / 64 * 64) + width ≤ 1024 := by
  have positive : 0 < 1025 - width := by omega
  have bound := Nat.mod_lt n positive
  have aligned := Nat.div_mul_le_self (n % (1025 - width)) 64
  omega

def boundedOffset (n width : Nat) (h : width ≤ 1024) :
    { offset : Nat // offset + width ≤ 1024 } :=
  ⟨n % (1025 - width) / 64 * 64, generatedOffsetInImage n width h⟩

theorem generatedBaseEffectiveAddress (target displacement : UInt64) :
    (target - displacement) + displacement = target :=
  UInt64.sub_add_cancel target displacement

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

def generatedState (occurrence : Occurrence) (address : Option SimpleAddress := none) : Generator NativeGen GeneratedCase := ⟨do
  let mut gprs ← chooseGprs.generate
  if let some a := address then
    let raw ← DataSource.chooseNat 0 1024
    if h : a.width ≤ 1024 then
      let offset := boundedOffset raw a.width h
      let target := UInt64.ofNat (0x100000000 + offset.val)
      gprs := gprs.set! a.base (target - a.displacement)
    else
      throw <| IO.userError "memory access exceeds the generated image"
  let flags ← chooseFlags.generate
  let memoryBytes ← chooseMemory.generate
  let vectorSeed ← (Generator.bytes 2112 2112).generate
  let sseRounding ← DataSource.chooseNat 0 3
  pure {
    occurrence
    gprs
    flags
    memoryAddress := 0x100000000
    memoryBytes
    vectorSeed
    sseRounding := UInt64.ofNat sseRounding
  }⟩

def generatedOccurrence (catalogue : Array Occurrence) : Generator NativeGen Occurrence := ⟨do
  if catalogue.isEmpty then throw <| IO.userError "cannot sample an empty instruction catalogue"
  let index ← DataSource.chooseNat 0 (catalogue.size - 1)
  let some occurrence := catalogue[index]? | throw <| IO.userError "catalogue occurrence index out of range"
  pure occurrence⟩

/-- Supply the generated instruction and concrete initial state to the native observer. -/
def GeneratedCase.observerRequest (c : GeneratedCase) : MovObserver.NativeObserver.Request :=
  { instruction := c.occurrence.bytes
    gprs := c.gprs
    flags := c.flags
    memory := #[{ address := c.memoryAddress, bytes := c.memoryBytes }]
    vectorSeed := some c.vectorSeed
    sseRounding := c.sseRounding }

end Wruh.IFormPbt
