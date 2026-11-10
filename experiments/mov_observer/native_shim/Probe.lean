import MemoryWrite
open MovObserver.NativeShim

private def readNat (stream : IO.FS.Handle) : IO Nat := do
  let line ← stream.getLine
  match line.trimAscii.toString.toNat? with
  | some n => pure n
  | none => throw <| IO.userError s!"invalid target line: {line}"

private def require (ok : Bool) (message : String) : IO Unit :=
  unless ok do throw (IO.userError message)

private def signalTarget (pid : Nat) (signal : String) : IO Unit := do
  let result ← IO.Process.output {
    cmd := "/run/current-system/sw/bin/kill", args := #[signal, toString pid] }
  require (result.exitCode == 0) result.stderr

def main (args : List String) : IO Unit := do
  let [python, target] := args | throw <| IO.userError "expected python and target paths"
  let child ← IO.Process.spawn {
    cmd := python, args := #[target], stdin := .piped, stdout := .piped }
  let pid ← readNat child.stdout
  let reaped ← IO.mkRef false
  try
    let a ← readNat child.stdout
    let b ← readNat child.stdout
    let c ← readNat child.stdout
    let mut stopped := false
    for _ in [:100] do
      let status ← IO.FS.readFile s!"/proc/{pid}/status"
      if (status.splitOn "\n").any (fun line => line.startsWith "State:" && line.contains 'T') then
        stopped := true
        break
      IO.sleep 10
    require stopped "target did not stop"
    let payload := ByteArray.mk ((List.range 1024).toArray.map fun i => UInt8.ofNat (i % 256))
    let ranges := #[(a, "abc".toUTF8), (b, "1234567".toUTF8), (c, payload)]
    for (address, bytes) in ranges do
      let raw ← writeMemoryOnce (UInt32.ofNat pid) (UInt64.ofNat address) bytes
      require (raw.toNat == bytes.size) s!"short/error syscall result: {raw}"
    let bad ← writeMemoryOnce (UInt32.ofNat pid) 0 "x".toUTF8
    require (bad.toInt64.toInt == -14) s!"expected EFAULT, got {bad.toInt64.toInt}"
    let empty ← writeMemoryOnce (UInt32.ofNat pid) 0 ByteArray.empty
    require (empty == 0) "empty transfer did not return zero"
    let mut consumed := 0
    for (_, bytes) in ranges do
      consumed := consumed + bytes.size
    require (consumed == 1034) "borrowed input sizes changed"
    require (ranges[0]!.2 == "abc".toUTF8 && ranges[1]!.2 == "1234567".toUTF8) "borrowed input bytes changed"
    for i in [:payload.size] do
      require (payload[i]! == UInt8.ofNat (i % 256)) "borrowed payload changed"
    child.stdin.putStrLn "check"
    child.stdin.flush
    signalTarget pid "-CONT"
    let response ← child.stdout.getLine
    require (response.startsWith "PASS:") response
    let exitCode ← child.wait
    reaped.set true
    require (exitCode == 0) "target failed"
    IO.println response.trimAscii.toString
    IO.println "PASS: raw -EFAULT and zero-length return paths"
  finally
    unless (← reaped.get) do
      let _ ← IO.Process.output {
        cmd := "/run/current-system/sw/bin/kill", args := #["-KILL", toString pid] }
      let _ ← child.wait
