import Hegel
import ExtractCase
import CompareCase
import ModelFootprint

open Lean Hegel Wruh.IFormPbt

structure Totals where
  matchedCount : Nat := 0
  mismatchCount : Nat := 0
  incomplete : Nat := 0
  errors : Nat := 0
  deriving Repr

private def metadata (python script : String) (bytes : ByteArray) : IO (Bool × UInt64 × Bool × Option SimpleAddress) := do
  let result ← IO.Process.output {cmd := python, args := #[script, instructionHex bytes]}
  if result.exitCode != 0 then throw <| IO.userError s!"decoder failed: {result.stderr}"
  let json ← match Json.parse result.stdout with
    | .ok value => pure value
    | .error error => throw <| IO.userError error
  match do
    let flow ← (← json.getObjVal? "fallthrough").getBool?
    let flags ← (← json.getObjVal? "defined_flags").getNat?
    let supported ← (← json.getObjVal? "address_supported").getBool?
    let value ← json.getObjVal? "address"
    let address ← if value == Json.null then pure none else do
      let base ← (← value.getObjVal? "base").getNat?
      let displacement ← (← value.getObjVal? "displacement").getNat?
      let width ← (← value.getObjVal? "width").getNat?
      pure <| some ({ base := base, displacement := UInt64.ofNat displacement, width := width } : SimpleAddress)
    pure (flow, UInt64.ofNat flags, supported, address) with
  | .ok result => pure result
  | .error error => throw <| IO.userError error

private def generatedInput (name : String) : Bool :=
  #["rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi",
    "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15", "rip",
    "d", "ac", "id", "rflags_CF", "rflags_PF", "rflags_AF", "rflags_ZF",
    "rflags_SF", "rflags_OF", "mem"].contains name || isVectorField name

def main (args : List String) : IO UInt32 := do
  let [cataloguePath, stubBuilder, wruh, metadataScript, fixtureDir, workDir,
      occurrencesArg, samplesArg, seedArg] := args
    | throw <| IO.userError "expected: CATALOGUE STUB_BUILDER WRUH METADATA FIXTURE_DIR WORK_DIR OCCURRENCES SAMPLES_PER_OCCURRENCE SEED"
  let some occurrenceBudget := occurrencesArg.toNat? | throw <| IO.userError "invalid occurrence budget"
  let some sampleBudget := samplesArg.toNat? | throw <| IO.userError "invalid sample budget"
  let some seed := seedArg.toNat? | throw <| IO.userError "invalid seed"
  if occurrenceBudget == 0 || sampleBudget == 0 then throw <| IO.userError "budgets must be positive"
  let some hegelLibrary ← IO.getEnv "WRUH_HEGEL_LIBRARY" | throw <| IO.userError "WRUH_HEGEL_LIBRARY is required"
  let some icedPython ← IO.getEnv "WRUH_ICED_PYTHON" | throw <| IO.userError "WRUH_ICED_PYTHON is required"
  let catalogue ← readCatalogue cataloguePath
  let loader ← IO.FS.readBinFile (fixtureDir ++ "/loader.bin")
  let capture ← IO.FS.readBinFile (fixtureDir ++ "/observer.bin")
  IO.FS.createDirAll workDir
  let engine ← FFI.Library.load hegelLibrary
  let totals ← IO.mkRef ({} : Totals)
  let settings : Hegel.Settings := {
    testCases := occurrenceBudget
    seed := some (UInt64.ofNat seed)
    phases := #[.reuse, .generate]
    database := .path (workDir ++ "/hegel-db")
    databaseKey := some "wruh-native-instruction"
    suppressHealthChecks := #[.tooSlow, .testCasesTooLarge, .largeInitialTestCase]
  }
  let result ← Hegel.check engine settings
      "Wruh model agrees with native instruction" fun testCase => do
    let occurrence ← testCase.draw (generatedOccurrence catalogue)
    let (fallthrough, definedFlags, addressSupported, address) ← metadata icedPython metadataScript occurrence.bytes
    let first ← testCase.draw (generatedState occurrence address)
    let mut cases := #[first]
    for _ in [1:sampleBudget] do
      cases := cases.push (← testCase.draw (generatedState first.occurrence address))
    let hex := instructionHex first.occurrence.bytes
    testCase.note s!"iform={first.occurrence.iform} bytes={hex}"
    try
      let artifactPath := System.FilePath.mk (workDir ++ "/model.json")
      let model ← first.extractModel stubBuilder wruh (workDir ++ "/fixture.elf") artifactPath "wruh_pbt_target"
      if !fallthrough then
        IO.println s!"INCOMPLETE {hex}: instruction does not fall through"
        totals.modify fun t => {t with incomplete := t.incomplete + sampleBudget}
        return true
      if !addressSupported then
        IO.println s!"INCOMPLETE {hex}: unsupported memory address shape"
        totals.modify fun t => {t with incomplete := t.incomplete + sampleBudget}
        return true
      let json ← match Json.parse (← IO.FS.readFile artifactPath) with
        | .ok json => pure json
        | .error error => throw <| IO.userError error
      let footprint ← match modelFootprint json "wruh_pbt_target" 0x400170 with
        | .ok footprint => pure footprint
        | .error error =>
          if error == "model contains scoped bindings that need dependency analysis" then
            IO.println s!"INCOMPLETE {hex}: {error}"
            totals.modify fun t => {t with incomplete := t.incomplete + sampleBudget}
            return true
          else throw <| IO.userError error
      let unknown := footprint.inputs.filter (fun name => !generatedInput name)
      if !unknown.isEmpty || !footprint.unobservedWrites.isEmpty then
        IO.println s!"INCOMPLETE {hex}: model inputs={unknown}, unobserved writes={footprint.unobservedWrites}"
        totals.modify fun t => {t with incomplete := t.incomplete + sampleBudget}
        return true
      let addresses ← match memoryAddressExprs json model footprint with
        | .ok addresses => pure addresses
        | .error error => throw <| IO.userError error
      let mut holds := true
      for i in [:sampleBudget] do
        let c := cases[i]!
        let outcome ← c.compare model (fun _ => some 0) (fun _ => 0) loader capture
          (workDir ++ "/native.elf") definedFlags footprint.guardInputs addresses
        match outcome with
        | .matched =>
          IO.println s!"MATCH {hex} {c.occurrence.iform} sample={i} rax={c.gprs[0]!} flags={c.flags} vector0={c.vectorSeed[0]!}"
          totals.modify fun t => {t with matchedCount := t.matchedCount + 1}
        | .mismatch differences =>
          holds := false
          testCase.note s!"bytes={hex} sample={i} gprs={c.gprs} flags={c.flags} memory={c.memoryBytes} vector={c.vectorSeed} rounding={c.sseRounding} differences={differences}"
          IO.println s!"MISMATCH {hex}: {differences}"
          totals.modify fun t => {t with mismatchCount := t.mismatchCount + 1}
        | .incomplete reason =>
          IO.println s!"INCOMPLETE {hex}: {reason}"
          totals.modify fun t => {t with incomplete := t.incomplete + 1}
      return holds
    catch error =>
      testCase.note s!"error for {hex}: {error}"
      IO.println s!"ERROR {hex}: {error}"
      totals.modify fun t => {t with errors := t.errors + 1}
      return false
  let counts ← totals.get
  IO.println s!"matches={counts.matchedCount} mismatches={counts.mismatchCount} incomplete={counts.incomplete} errors={counts.errors} hegel={reprStr result.status}"
  for report in result.reproductions do
    unless report.isEmpty do IO.println report
  if result.status != .passed || counts.mismatchCount != 0 || counts.errors != 0 || counts.matchedCount == 0 then return 1
  return 0
