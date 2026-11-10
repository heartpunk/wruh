import Observer
open MovObserver.NativeObserver

def require (ok : Bool) (message : String) : IO Unit :=
  unless ok do throw <| IO.userError message

def laneOffset (l : VectorLayout) (r lane : Nat) : Nat :=
  if r ≥ 16 then l.hi16+(r-16)*64+lane*8
  else if lane < 2 then 160+r*16+lane*8
  else if lane < 4 then l.ymm+r*16+(lane-2)*8
  else l.zmmHi+r*32+(lane-4)*8

def laneValue (r lane : Nat) : UInt64 := UInt64.ofNat (0x1020304000000000+r*257+lane*19)

def main (args : List String) : IO Unit := do
  let [fixtureDir,workDir] := args | throw <| IO.userError "expected fixtures and work directory"
  let some l ← vectorLayout | throw <| IO.userError "vector trials require CPU XSAVE and OSXSAVE feature bits"
  let features ← cpuid 7 0
  require ((l.enabled &&& 0xe6) == 0xe6 && (dword features 4 &&& 0x40010020) == 0x40010020)
    "these concrete trials require OS-enabled AVX2, AVX512F and AVX512BW"
  IO.println s!"vector layout: {repr l}"
  let loader ← IO.FS.readBinFile (fixtureDir ++ "/loader.bin")
  let capture ← IO.FS.readBinFile (fixtureDir ++ "/observer.bin")
  let address : UInt64 := 0x100000ffc
  let gprs := ((List.range 16).toArray.map (fun i => UInt64.ofNat (0x12340000+37*i))).set! 7 address
  let bytes := ByteArray.mk ((List.range 1024).toArray.map (fun i => UInt8.ofNat (i*17+29)))
  let r : Request := {instruction := ByteArray.mk #[0x90],gprs,flags := 0x202,memory := #[⟨address,bytes⟩]}
  let baseline ← observeFallthrough loader capture (workDir ++ "/vector-baseline.elf") r
  let some initial := baseline.installedXstate | throw <| IO.userError "no xstate image"
  let mut image := putWord initial 512 (word initial 512 ||| 0xe6)
  for reg in [:32] do
    for lane in [:8] do image := putWord image (laneOffset l reg lane) (laneValue reg lane)
  for k in [:8] do image := putWord image (l.masks+8*k) (UInt64.ofNat (0x55+k*17))
  let names := #["paddq-xmm","vpxor-ymm","vpaddq-zmm","vpaddq-merge-high","vpaddq-zero-high","vmovdqu64-store","kxorq"]
  let mut failures := 0
  for index in [:names.size] do
    let name := names[index]!
    try
      let instruction ← IO.FS.readBinFile (fixtureDir ++ s!"/../native_observer/out/{name}.bin")
      let result ← observeFallthrough loader capture (workDir ++ s!"/{name}.elf") {r with instruction, xstate := some image}
      let some installed := result.installedXstate | throw <| IO.userError "missing installed xstate"
      let some terminal := result.terminalXstate | throw <| IO.userError "missing terminal xstate"
      for (suffix,data) in #[("requested",image),("installed",installed),("terminal",terminal)] do
        IO.FS.writeBinFile (workDir ++ s!"/{name}-{suffix}.bin") data
      let mut expected := image
      let mut expectedMemory := bytes
      if index == 0 then
        for lane in [:2] do expected := putWord expected (laneOffset l 0 lane) (laneValue 0 lane + laneValue 1 lane)
      else if index == 1 then
        for lane in [:8] do
          expected := putWord expected (laneOffset l 0 lane) (if lane < 4 then laneValue 1 lane ^^^ laneValue 2 lane else 0)
      else if index == 2 then
        for lane in [:8] do expected := putWord expected (laneOffset l 0 lane) (laneValue 1 lane + laneValue 2 lane)
      else if index == 3 || index == 4 then
        for lane in [:8] do
          let active := (word image (l.masks+8) &&& (1 <<< UInt64.ofNat lane)) != 0
          expected := putWord expected (laneOffset l 16 lane)
            (if active then laneValue 17 lane + laneValue 18 lane else if index == 4 then 0 else laneValue 16 lane)
      else if index == 5 then
        for lane in [:8] do expectedMemory := putWord expectedMemory (8*lane) (laneValue 31 lane)
      else expected := putWord expected (l.masks+24) (word image (l.masks+8) ^^^ word image (l.masks+16))
      require ((← vectorBytes l terminal) == (← vectorBytes l expected)) "vector/mask state differs"
      require (result.gprs == gprs && result.terminalFlags == 0x202) "GPR/flags differ"
      require (result.memory[0]!.bytes == expectedMemory) "sparse memory differs"
      for i in [:160] do
        if fpStateByte i then require (result.terminalFp[i]! == result.installedFp[i]!) s!"nonvector FP changed at {i}"
      IO.println s!"PASS {name}: all 32 ZMMs, eight masks, GPRs/flags, legacy FP and 1024 memory bytes"
    catch e =>
      failures := failures+1
      IO.println s!"FAIL {name}: {e}"
  if failures != 0 then throw <| IO.userError s!"{failures} vector examples failed"
  IO.println "PASS: seven concrete vector observations"
