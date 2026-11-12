import Hegel
import ExtractCase
import CompareCase
import ModelFootprint

open Lean Hegel Wruh.IFormPbt

structure Totals where
  matchedCount : Nat := 0
  mismatchCount : Nat := 0
  incompleteOccurrences : Nat := 0
  incompleteStates : Nat := 0
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

private def saveFailure (workDir : String) (seed : Nat) (occurrenceIndex sample serial : Nat)
    (c : GeneratedCase) (reason : String) : IO Unit := do
  let o := c.occurrence
  let payload := Json.mkObj [
    ("seed", toJson seed), ("occurrence_index", toJson occurrenceIndex),
    ("sample", toJson sample), ("iform", toJson o.iform),
    ("instruction_bytes", toJson (instructionHex o.bytes)),
    ("target_id", toJson o.targetId), ("binary_sha256", toJson o.binarySha256),
    ("function_id", toJson o.functionId), ("address", toJson o.address),
    ("occurrence_id", toJson o.occurrenceId),
    ("gprs", toJson (c.gprs.map UInt64.toNat)), ("flags", toJson c.flags.toNat),
    ("memory_address", toJson c.memoryAddress.toNat),
    ("memory_hex", toJson (instructionHex c.memoryBytes)),
    ("vector_hex", toJson (instructionHex c.vectorSeed)),
    ("sse_rounding", toJson c.sseRounding.toNat), ("reason", toJson reason)]
  let path := s!"{workDir}/failure-{seed}-{occurrenceIndex}-{sample}-{serial}.json"
  IO.FS.writeFile path payload.compress
  IO.println s!"FAILURE_WITNESS {path}"

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
  let candidates := sampleOccurrences catalogue catalogue.size (UInt64.ofNat seed)
  let seenStates ← IO.mkRef (#[] : Array StateIdentity)
  let failed ← IO.mkRef false
  let testedOccurrences ← IO.mkRef 0
  let completedOccurrences ← IO.mkRef 0
  let candidatesExamined ← IO.mkRef 0
  let stateShortfall ← IO.mkRef 0
  IO.println s!"candidate_occurrences={candidates.size} requested_occurrences={occurrenceBudget} seed={seed}"
  for occurrenceIndex in [:candidates.size] do
    if (← completedOccurrences.get) ≥ occurrenceBudget then break
    candidatesExamined.modify (· + 1)
    let occurrence := candidates[occurrenceIndex]!
    let occurrenceKey := s!"{occurrence.targetId}:{occurrence.binarySha256}:{occurrence.functionId}:{occurrence.address}:{occurrence.occurrenceId}"
    let hex := instructionHex occurrence.bytes
    IO.println s!"OCCURRENCE index={occurrenceIndex} id={occurrenceKey} iform={occurrence.iform} bytes={hex}"
    try
      let (fallthrough, definedFlags, addressSupported, address) ← metadata icedPython metadataScript occurrence.bytes
      if !fallthrough then
        IO.println s!"INCOMPLETE {hex}: instruction does not fall through"
        totals.modify fun t => {t with incompleteOccurrences := t.incompleteOccurrences + 1}
        continue
      if !addressSupported then
        IO.println s!"INCOMPLETE {hex}: unsupported memory address shape"
        totals.modify fun t => {t with incompleteOccurrences := t.incompleteOccurrences + 1}
        continue
      let first : GeneratedCase := ⟨occurrence, #[], 0, 0, ByteArray.empty, ByteArray.empty, 0⟩
      let artifactPath := System.FilePath.mk (workDir ++ "/model.json")
      let model ← first.extractModel stubBuilder wruh (workDir ++ "/fixture.elf") artifactPath "wruh_pbt_target"
      let json ← match Json.parse (← IO.FS.readFile artifactPath) with
        | .ok json => pure json
        | .error error => throw <| IO.userError error
      let footprint ← match modelFootprint json "wruh_pbt_target" 0x400170 with
        | .ok footprint => pure footprint
        | .error error =>
          if error == "model contains scoped bindings that need dependency analysis" then
            IO.println s!"INCOMPLETE {hex}: {error}"
            totals.modify fun t => {t with incompleteOccurrences := t.incompleteOccurrences + 1}
            continue
          else throw <| IO.userError error
      let unknown := footprint.inputs.filter (fun name => !generatedInput name)
      if !unknown.isEmpty || !footprint.unobservedWrites.isEmpty then
        IO.println s!"INCOMPLETE {hex}: model inputs={unknown}, unobserved writes={footprint.unobservedWrites}"
        totals.modify fun t => {t with incompleteOccurrences := t.incompleteOccurrences + 1}
        continue
      let addresses ← match memoryAddressExprs json model footprint with
        | .ok addresses => pure addresses
        | .error error => throw <| IO.userError error
      let accepted ← IO.mkRef 0
      let comparisons ← IO.mkRef 0
      let failureSerial ← IO.mkRef 0
      let failedStates ← IO.mkRef (#[] : Array StateIdentity)
      let settings : Hegel.Settings := {
        testCases := sampleBudget * 8
        seed := some (UInt64.ofNat seed + UInt64.ofNat occurrenceIndex)
        phases := #[.reuse, .generate]
        database := .path (workDir ++ "/hegel-db")
        databaseKey := some ("wruh-native-instruction:" ++ occurrenceKey)
        suppressHealthChecks := #[.tooSlow, .testCasesTooLarge, .largeInitialTestCase]
      }
      let result ← Hegel.check engine settings
          "Wruh model agrees with native instruction" fun testCase => do
        if (← accepted.get) ≥ sampleBudget && (← failedStates.get).isEmpty then return true
        let c ← testCase.draw (generatedState occurrence address)
        let id := c.stateIdentity
        let replayingFailure := (← failedStates.get).contains id
        if (← accepted.get) ≥ sampleBudget && !replayingFailure then return true
        if (← seenStates.get).contains id && !replayingFailure then return true
        let i ← accepted.get
        testCase.note s!"seed={seed} occurrence={occurrenceKey} iform={occurrence.iform} bytes={hex} sample={i} gprs={c.gprs} flags={c.flags} memoryAddress={c.memoryAddress} memory={c.memoryBytes} vector={c.vectorSeed} rounding={c.sseRounding}"
        try
          let outcome ← c.compare model (fun _ => some 0) (fun _ => 0) loader capture
            (workDir ++ "/native.elf") definedFlags footprint.guardInputs addresses
          match outcome with
          | .matched =>
            if replayingFailure then
              IO.println s!"FAILURE_REPLAY_DID_NOT_REPRODUCE {hex}"
            else
              seenStates.modify (·.push id)
              accepted.modify (· + 1)
              comparisons.modify (· + 1)
              IO.println s!"MATCH {hex} {occurrence.iform} sample={i} rax={c.gprs[0]!} flags={c.flags} vector0={c.vectorSeed[0]!}"
              totals.modify fun t => {t with matchedCount := t.matchedCount + 1}
            return true
          | .mismatch differences =>
            testCase.note s!"differences={differences}"
            if replayingFailure then
              IO.println s!"FAILURE_REPLAY {hex}: {differences}"
            else
              failedStates.modify (·.push id)
              seenStates.modify (·.push id)
              accepted.modify (· + 1)
              comparisons.modify (· + 1)
              let serial ← failureSerial.get
              failureSerial.modify (· + 1)
              saveFailure workDir seed occurrenceIndex i serial c (reprStr differences)
              IO.println s!"MISMATCH {hex}: {differences}"
              totals.modify fun t => {t with mismatchCount := t.mismatchCount + 1}
            return false
          | .incomplete reason =>
            if replayingFailure then
              IO.println s!"FAILURE_REPLAY_INCOMPLETE {hex}: {reason}"
            else
              seenStates.modify (·.push id)
              IO.println s!"INCOMPLETE {hex}: {reason}"
              totals.modify fun t => {t with incompleteStates := t.incompleteStates + 1}
            return true
        catch error =>
          testCase.note s!"error for {hex}: {error}"
          if replayingFailure then
            IO.println s!"FAILURE_REPLAY_ERROR {hex}: {error}"
          else
            failedStates.modify (·.push id)
            seenStates.modify (·.push id)
            let serial ← failureSerial.get
            failureSerial.modify (· + 1)
            saveFailure workDir seed occurrenceIndex i serial c (toString error)
            IO.println s!"ERROR {hex}: {error}"
            totals.modify fun t => {t with errors := t.errors + 1}
          return false
      if result.status != .passed then failed.set true
      for report in result.reproductions do
        unless report.isEmpty do IO.println report
      if (← comparisons.get) > 0 then testedOccurrences.modify (· + 1)
      if (← comparisons.get) ≥ sampleBudget then completedOccurrences.modify (· + 1)
      let shortfall := sampleBudget - (← accepted.get)
      if shortfall > 0 then
        IO.println s!"STATE_SHORTFALL {hex}: {shortfall} comparisons not reached within generation budget"
        stateShortfall.modify (· + shortfall)
    catch error =>
      IO.println s!"ERROR {hex}: {error}"
      totals.modify fun t => {t with errors := t.errors + 1}
      failed.set true
  let counts ← totals.get
  let uniqueStates := (← seenStates.get).size
  let tested ← testedOccurrences.get
  let completed ← completedOccurrences.get
  let examined ← candidatesExamined.get
  let missing := occurrenceBudget - completed
  let missingStates ← stateShortfall.get
  let comparisons := counts.matchedCount + counts.mismatchCount
  let comparisonShortfall := occurrenceBudget * sampleBudget - comparisons
  IO.println s!"requested_occurrences={occurrenceBudget} candidates_examined={examined} tested_occurrences={tested} completed_occurrences={completed} occurrence_shortfall={missing} distinct_states={uniqueStates} comparisons={comparisons} comparison_shortfall={comparisonShortfall} matches={counts.matchedCount} mismatches={counts.mismatchCount} incomplete_occurrences={counts.incompleteOccurrences} incomplete_states={counts.incompleteStates} state_shortfall={missingStates} errors={counts.errors}"
  if (← failed.get) || counts.mismatchCount != 0 || counts.errors != 0 || missing != 0 then return 1
  return 0
