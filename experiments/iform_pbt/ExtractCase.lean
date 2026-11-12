import GeneratedCase
import Wruh.IFormPbt.ExtractedTarget

namespace Wruh.IFormPbt

private def hexByte (b : UInt8) : String := Id.run do
  let digits := "0123456789abcdef".toList.toArray
  let n := b.toNat
  return String.ofList [digits[n / 16]!, digits[n % 16]!]

private def checkedProcess (cmd : String) (args : Array String) : IO Unit := do
  let result ← IO.Process.output { cmd, args }
  if result.exitCode != 0 then
    throw <| IO.userError s!"{cmd} failed ({result.exitCode}): {result.stderr}"

/-- Extract the sampled bytes through the regular Wruh CLI and read its model. -/
def GeneratedCase.extractModel (c : GeneratedCase) (stubBuilder wruh : String)
    (elfPath artifactPath : System.FilePath) (functionId : String) : IO ExtractedTarget := do
  let bytes := String.join (c.occurrence.bytes.data.toList.map hexByte)
  checkedProcess stubBuilder #[bytes, elfPath.toString]
  checkedProcess wruh #["--artifact", elfPath.toString, "--root", functionId,
    "--root-only", "--output", artifactPath.toString]
  let json ← match Lean.Json.parse (← IO.FS.readFile artifactPath) with
    | .ok value => pure value
    | .error error => throw <| IO.userError error
  match readExtractedTarget json functionId c.occurrence.bytes with
  | .ok model => pure model
  | .error error => throw <| IO.userError error

end Wruh.IFormPbt
