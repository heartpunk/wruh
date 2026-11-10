import Observer
open MovObserver.NativeObserver

-- Concrete smoke examples, not a generated semantics campaign.
def set16 (b : ByteArray) (i : Nat) (v : UInt16) : ByteArray :=
  (b.set! i v.toUInt8).set! (i+1) (v >>> 8).toUInt8

def get16 (b : ByteArray) (i : Nat) : UInt64 := word b i &&& 0xffff

def ext80 (b : ByteArray) (slot : Nat) (significand : UInt64) (exponent : UInt16) : ByteArray :=
  set16 (putWord b (32+16*slot) significand) (40+16*slot) exponent

def require (ok : Bool) (message : String) : IO Unit :=
  unless ok do throw <| IO.userError message

structure Example where
  name : String
  instruction : Array UInt8
  fp : ByteArray
  memory : ByteArray
  expectedLow : UInt64 := 0
  expectedMxcsr : UInt64 := 0x1f80
  x87 : Bool := false
  expectedTop : UInt64 := 3
  expectedTag : UInt8 := 0
  expectedSignificand : UInt64 := 0
  expectedExponent : UInt64 := 0
  store80 : Bool := false

def main (args : List String) : IO Unit := do
  let [fixtureDir, workDir] := args | throw <| IO.userError "expected fixture directory and work directory"
  let loader ← IO.FS.readBinFile (fixtureDir ++ "/loader.bin")
  let capture ← IO.FS.readBinFile (fixtureDir ++ "/observer.bin")
  let address : UInt64 := 0x100000ffc
  let gprs := ((List.range 16).toArray.map (fun i => UInt64.ofNat (0x12340000+37*i))).set! 7 address
  let memory := ByteArray.mk ((List.range 1024).toArray.map (fun i => UInt8.ofNat (i*17+29)))
  let request : Request := { instruction := ByteArray.mk #[0x90], gprs, flags := 0x202, memory := #[⟨address,memory⟩] }
  let baseline ← observeFallthrough loader capture (workDir ++ "/fp-baseline.elf") request
  -- Start with an actual kernel image; retain its capability metadata/padding.
  let mut base := baseline.installedFp
  base := set16 base 0 0x037f -- all x87 exceptions masked, extended precision, nearest
  base := set16 base 2 (3*2048) -- nonzero TOP deliberately
  base := base.set! 4 0
  base := set16 base 6 0
  base := putWord (putWord base 8 0) 16 0
  for i in [:8] do base := ext80 base i 0 0
  -- putWord spans MXCSR and its mask: preserve the kernel-reported upper word.
  base := putWord base 24 ((word base 24 &&& 0xffffffff00000000) ||| 0x1f80)
  for i in [:16] do
    base := putWord (putWord base (160+16*i) (UInt64.ofNat (0x123400+i)))
      (168+16*i) (UInt64.ofNat (0xabcdef00+i))
  let operands := putWord (putWord base 160 0x3ff8000000000000) 176 0x4002000000000000
  let stack := ext80 (ext80 (base.set! 4 0x18) 0 0xc000000000000000 0x3fff) 1 0x9000000000000000 0x4000
  let roundUp := putWord (putWord (putWord base 160 0x3ff0000000000000) 176 0x3ca0000000000000)
    24 ((word base 24 &&& 0xffffffff00000000) ||| 0x5f80)
  let examples : Array Example := #[
    { name := "fld-m64", instruction := #[0xdd,0x07], fp := base,
      memory := putWord memory 0 0x3ff8000000000000, x87 := true,
      expectedTop := 2, expectedTag := 4, expectedSignificand := 0xc000000000000000, expectedExponent := 0x3fff },
    { name := "fadd-st0-st1", instruction := #[0xd8,0xc1], fp := stack, memory,
      x87 := true, expectedTag := 0x18, expectedSignificand := 0xf000000000000000, expectedExponent := 0x4000 },
    { name := "fstp-m80", instruction := #[0xdb,0x3f], fp := stack, memory,
      x87 := true, expectedTop := 4, expectedTag := 0x10, store80 := true,
      expectedSignificand := 0x9000000000000000, expectedExponent := 0x4000 },
    { name := "addsd", instruction := #[0xf2,0x0f,0x58,0xc1], fp := operands, memory,
      expectedLow := 0x400e000000000000 },
    { name := "divsd-masked-zero", instruction := #[0xf2,0x0f,0x5e,0xc1],
      fp := putWord (putWord base 160 0x3ff0000000000000) 176 0, memory,
      expectedLow := 0x7ff0000000000000, expectedMxcsr := 0x1f84 },
    { name := "addsd-round-up", instruction := #[0xf2,0x0f,0x58,0xc1], fp := roundUp, memory,
      expectedLow := 0x3ff0000000000001, expectedMxcsr := 0x5fa0 }
  ]
  let mut failures := 0
  for t in examples do
    try
      let r := { request with instruction := ByteArray.mk t.instruction, memory := #[⟨address,t.memory⟩], fp := some t.fp }
      let result ← observeFallthrough loader capture (workDir ++ s!"/{t.name}.elf") r
      for (suffix, bytes) in #[("requested",t.fp),("installed",result.installedFp),("terminal",result.terminalFp)] do
        IO.FS.writeBinFile (workDir ++ s!"/{t.name}-{suffix}.bin") bytes
      require (result.gprs == gprs && result.terminalFlags == 0x202) "GPR/flags changed"
      let expectedMemory := if t.store80 then set16 (putWord t.memory 0 0xc000000000000000) 8 0x3fff else t.memory
      require (result.memory[0]!.bytes == expectedMemory) "sparse memory differs"
      let f := result.terminalFp
      if t.x87 then
        require (get16 f 0 == 0x037f) "x87 control changed"
        require (((get16 f 2 >>> 11) &&& 7) == t.expectedTop && f[4]! == t.expectedTag) "x87 TOP/tag differs"
        require ((get16 f 2 &&& 0xff) == 0) "unexpected x87 exception status"
        require (word f 32 == t.expectedSignificand && get16 f 40 == t.expectedExponent) "ST0 payload differs"
        for i in [:416] do
          if 24 ≤ i && i < 28 || 160 ≤ i then
            require (f[i]! == t.fp[i]!) s!"unaffected scalar/vector state changed at {i}"
        -- FIP/FDP/FOP and undefined x87 condition bits are retained, not fixed expectations.
      else
        let expected := putWord (putWord t.fp 160 t.expectedLow) 24
          ((word t.fp 24 &&& 0xffffffff00000000) ||| t.expectedMxcsr)
        for i in [:512] do
          if fpStateByte i then require (f[i]! == expected[i]!) s!"FP state differs at {i}: got {f[i]!}, expected {expected[i]!}"
      IO.println s!"PASS {t.name}: ST0 significand={word f 32} exponent={get16 f 40} FSW={get16 f 2} FTW={f[4]!} XMM0.low={word f 160} MXCSR={word f 24 &&& 0xffffffff}; GPRs/flags/memory checked"
    catch e =>
      failures := failures+1
      IO.println s!"FAIL {t.name}: {e}"
  if failures != 0 then throw <| IO.userError s!"{failures} FP examples failed"
  IO.println "PASS: six concrete FP observations; raw requested/installed/terminal images retained"
