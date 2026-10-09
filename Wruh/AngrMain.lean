import Wruh.AngrDriver

/-! Lean owns the extraction loop; Python is a persistent angr worker. -/
namespace Wruh.AngrMain

open Lean Ayxg.QfAbv Ayxg.QfAbv.JsonCodec Wruh.AngrDriver

private def checked {α : Type} : Except String α → IO α
  | .ok value => pure value
  | .error message => throw (IO.userError message)

private def readJson (output : IO.FS.Handle) : IO Json := do
  let line ← output.getLine
  if line.isEmpty then throw (IO.userError "angr worker closed its output")
  checked (Json.parse line)

private def stringField (object : Json) (name : String) : IO String :=
  checked do
    let value ← field object name
    value.getStr?

private def arrayField (object : Json) (name : String) : IO (Array Json) :=
  checked do
    let value ← field object name
    value.getArr?

private def request (input output : IO.FS.Handle) (address : Nat) : IO Json := do
  input.putStrLn ((Json.mkObj [("op", toJson "step"), ("address", toJson address)]).compress)
  input.flush
  readJson output

private partial def splitArgs : List String → Option String → Array String →
    Except String (String × Array String)
  | [], some output, workerArgs => pure (output, workerArgs)
  | [], none, _ => throw "--output PATH is required"
  | "--output" :: output :: rest, _, workerArgs => splitArgs rest (some output) workerArgs
  | "--output" :: [], _, _ => throw "--output requires a path"
  | argument :: rest, output, workerArgs => splitArgs rest output (workerArgs.push argument)

private def runFunction (Γ : Ctx) (input output : IO.FS.Handle)
    (declarations architecture : Json) (function : Json)
    (roots : Array (TypedExpr Γ)) : IO (Json × Array (TypedExpr Γ)) := do
  let functionId ← stringField function "function_id"
  let entry ← checked (natField function "entry")
  let siteRecords ← arrayField function "sites"
  let mut sites : List (Site Γ) := []
  let mut occurrences : List Json := []
  for record in siteRecords do
    let address ← checked (natField record "address")
    let occurrence ← checked (field record "occurrence")
    let occurrenceId ← checked (natField occurrence "static_occurrence_id")
    let response ← request input output address
    sites := (← checked (parseSite Γ address occurrenceId response)) :: sites
    occurrences := occurrence :: occurrences
  pure <| (functionJson declarations architecture functionId entry
    occurrences.reverse sites.reverse).run roots

private def run (args : List String) : IO Unit := do
  let (outputPath, workerArgs) ← checked (splitArgs args none #[])
  let some ayxgSource ← IO.getEnv "WRUH_AYXG_SOURCE"
    | throw (IO.userError "WRUH_AYXG_SOURCE must name the AYXG expression-parity source")
  let cwd ← IO.currentDir
  let priorPythonPath ← IO.getEnv "PYTHONPATH"
  let pythonPath := ayxgSource ++ "/python:" ++ cwd.toString ++
    (priorPythonPath.map (":" ++ ·) |>.getD "")
  let python ← match ← IO.getEnv "WRUH_PYTHON" with
    | some path => pure path
    | none =>
      match ← IO.getEnv "GHOT_NIX_ANGR_ROOT" with
      | some root => pure (root ++ "/bin/python3")
      | none => pure "python3"
  let child ← IO.Process.spawn {
    cmd := python
    args := #["-m", "extractor.lean_angr_worker"] ++ workerArgs
    stdin := .piped
    stdout := .piped
    stderr := .inherit
    env := #[("PYTHONPATH", some pythonPath)]
  }
  let inventory ← readJson child.stdout
  if (← stringField inventory "kind") != "inventory" then
    throw (IO.userError "angr worker did not return an inventory")
  let declarations ← checked (field inventory "declarations")
  let Γ ← checked (do
    let records ← declarations.getArr?
    records.toList.mapM parseDecl)
  let architecture ← checked (field inventory "architecture")
  let functionRecords ← arrayField inventory "functions"
  let mut roots : Array (TypedExpr Γ) := #[]
  let mut functions : Array Json := #[]
  for function in functionRecords do
    let (result, nextRoots) ← runFunction Γ child.stdin child.stdout
      declarations architecture function roots
    roots := nextRoots
    functions := functions.push result
  child.stdin.putStrLn ((Json.mkObj [("op", toJson "quit")]).compress)
  child.stdin.flush
  let status ← child.wait
  if status != 0 then throw (IO.userError s!"angr worker exited with status {status}")
  let document ← checked (bundleJson inventory functions.toList roots)
  IO.FS.writeFile (System.FilePath.mk outputPath) (document.compress ++ "\n")

end Wruh.AngrMain

def main (args : List String) : IO UInt32 := do
  Wruh.AngrMain.run args
  pure 0
