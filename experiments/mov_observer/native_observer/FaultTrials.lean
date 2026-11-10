import Observer
open MovObserver.NativeObserver

def require (ok : Bool) (message : String) : IO Unit :=
  unless ok do throw <| IO.userError message

structure FaultExample where
  name : String
  instruction : Array UInt8
  signal : UInt64
  code : Int
  address : UInt64
  partialCopy : Bool := false

def main (args : List String) : IO Unit := do
  let [fixtureDir,workDir] := args | throw <| IO.userError "expected fixtures and work directory"
  let loader ← IO.FS.readBinFile (fixtureDir ++ "/loader.bin")
  let capture ← IO.FS.readBinFile (fixtureDir ++ "/observer.bin")
  let source : UInt64 := 0x100000010
  let destination : UInt64 := 0x200000fff
  let gprs := ((List.range 16).toArray.map (fun i => UInt64.ofNat (0x12340000+37*i)))
    |>.set! 0 123 |>.set! 1 0 |>.set! 2 0 |>.set! 6 source |>.set! 7 0x300000000
  let memory : Array Region := #[⟨source,ByteArray.mk #[0xab,0xcd,0xef,0x42]⟩,⟨destination,ByteArray.mk #[0x11]⟩]
  let base : Request := {instruction := ByteArray.mk #[0x90],gprs,flags := 0x202,memory}
  let baseline ← observeFallthrough loader capture (workDir ++ "/fault-baseline.elf") base
  let layout ← vectorLayout
  let mut state := baseline.installedXstate
  if let some l := layout then
    if let some b := state then
      let mut b := b
      for (bit,offset,size) in (#[(1,160,256),(2,l.ymm,256),(5,l.masks,64),(6,l.zmmHi,512),(7,l.hi16,1024)] : Array (Nat × Nat × Nat)) do
        if (l.enabled &&& (1 <<< UInt64.ofNat bit)) != 0 then
          b := putWord b 512 (word b 512 ||| (1 <<< UInt64.ofNat bit))
          for j in [:size] do b := b.set! (offset+j) (UInt8.ofNat (j*17+bit*13))
      state := some b
  let examples : Array FaultExample := #[
    {name := "div-zero",instruction := #[0x48,0xf7,0xf1],signal := 8,code := 1,address := UInt64.ofNat target},
    {name := "unmapped-load",instruction := #[0x48,0x8b,0x07],signal := 11,code := 1,address := 0x300000000},
    {name := "ud2",instruction := #[0x0f,0x0b],signal := 4,code := 2,address := UInt64.ofNat target},
    {name := "rep-partial-store",instruction := #[0xf3,0xa4],signal := 11,code := 1,address := destination+1,partialCopy := true}
  ]
  for t in examples do
    let requested := if t.partialCopy then (gprs.set! 1 2).set! 7 destination else gprs
    let r := {base with instruction := ByteArray.mk t.instruction,gprs := requested,xstate := state}
    let result ← observeInstruction loader capture (workDir ++ s!"/{t.name}.elf") r
    let some fault := result.fault | throw <| IO.userError s!"{t.name}: unexpectedly succeeded"
    require (fault.signal == t.signal && fault.code == t.code && fault.address == some t.address) s!"{t.name}: wrong fault metadata"
    require (word result.rawTerminalRegisters (16*8) == UInt64.ofNat target) "wrong restart PC"
    let expected := if t.partialCopy then ((requested.set! 1 1).set! 6 (source+1)).set! 7 (destination+1) else requested
    require (result.gprs == expected) s!"{t.name}: fault GPR state differs"
    -- Hardware may set RF in the saved fault context. Retain it; compare modeled flags.
    require ((result.terminalFlags &&& 0x240cd5) == (r.flags &&& 0x240cd5)) "modeled flags changed"
    require (result.memory[0]!.bytes == memory[0]!.bytes && result.memory[1]!.bytes ==
      (if t.partialCopy then ByteArray.mk #[0xab] else memory[1]!.bytes)) "partial memory effects differ"
    for i in [:512] do
      if fpStateByte i then require (result.installedFp[i]! == result.terminalFp[i]!) s!"FP changed at {i}"
    if let some l := layout then
      let some before := result.installedXstate | throw <| IO.userError "missing installed xstate"
      let some after := result.terminalXstate | throw <| IO.userError "missing fault xstate"
      require ((← vectorBytes l before) == (← vectorBytes l after)) "vector state changed"
      IO.FS.writeBinFile (workDir ++ s!"/{t.name}-xstate.bin") after
    IO.FS.writeBinFile (workDir ++ s!"/{t.name}-siginfo.bin") fault.rawSiginfo
    IO.FS.writeBinFile (workDir ++ s!"/{t.name}-registers.bin") result.rawTerminalRegisters
    IO.FS.writeBinFile (workDir ++ s!"/{t.name}-fp.bin") result.terminalFp
    IO.println s!"PASS {t.name}: signal={fault.signal}, code={fault.code}, address={repr fault.address}, RIP={word result.rawTerminalRegisters (16*8)}, RFLAGS={result.terminalFlags}, RCX={result.gprs[1]!}; GPR/FP/memory checked, extended-vector check={layout.isSome}"
  -- A loader fault must remain a harness error, not a target observation.
  let broken := (loader.set! 0 0x0f).set! 1 0x0b
  let mut rejected := false
  try
    let _ ← observeInstruction broken capture (workDir ++ "/broken-loader.elf") base
  catch e =>
    require (e.toString.startsWith "unexpected stop outside supported target outcome") s!"unrelated harness failure: {e}"
    rejected := true
  require rejected "loader fault was accepted as target output"
  IO.println "PASS: four native target faults, including partial REP effects; loader fault rejected"
