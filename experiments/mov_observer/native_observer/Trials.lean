import Observer
open MovObserver.NativeObserver

structure Trial where
  name : String
  instruction : Array UInt8
  rax : UInt64 := 0
  rbx : UInt64 := 0
  rcx : UInt64 := 0
  flags : UInt64 := 0x202
  expectedRax : UInt64 := 0
  expectedRcx : UInt64 := 0
  expectedFlags : UInt64 := 0x202
  flagsMask : UInt64 := 0xffffffffffffffff
  stores : Bool := false
  deriving Inhabited

def trials : Array Trial := #[
  { name := "mov rax, rbx", instruction := #[0x48,0x89,0xd8], rax := 7, rbx := 42, expectedRax := 42 },
  { name := "add rax, rbx", instruction := #[0x48,0x01,0xd8], rax := 0xffffffffffffffff, rbx := 1, expectedFlags := 0x257 },
  { name := "adc rax, rbx", instruction := #[0x48,0x11,0xd8], rax := 5, rbx := 7, flags := 0x203, expectedRax := 13 },
  { name := "sub rax, rbx", instruction := #[0x48,0x29,0xd8], rax := 0, rbx := 1, expectedRax := 0xffffffffffffffff, expectedFlags := 0x297 },
  { name := "xor rax, rax", instruction := #[0x48,0x31,0xc0], rax := 123, expectedFlags := 0x246, flagsMask := 0xffffffffffffffef },
  { name := "shl rax, 1", instruction := #[0x48,0xd1,0xe0], rax := 0x8000000000000001, expectedRax := 2, expectedFlags := 0xa03, flagsMask := 0xffffffffffffffef },
  { name := "cmp rax, rbx", instruction := #[0x48,0x39,0xd8], rax := 23, rbx := 23, expectedRax := 23, expectedFlags := 0x246 },
  { name := "cmovz rcx, rbx", instruction := #[0x48,0x0f,0x44,0xcb], rbx := 99, rcx := 4, flags := 0x242, expectedRcx := 99, expectedFlags := 0x242 },
  { name := "mov rax, [rdi]", instruction := #[0x48,0x8b,0x07], expectedRax := 0x8877665544332211, flags := 0x602, expectedFlags := 0x602 },
  { name := "mov [rdi], rax", instruction := #[0x48,0x89,0x07], rax := 0xdeadbeef01234567, expectedRax := 0xdeadbeef01234567, stores := true }
]

def main (args : List String) : IO Unit := do
  let [fixtureDir, workDir] := args | throw <| IO.userError "expected fixture directory and work directory"
  let loader ← IO.FS.readBinFile (fixtureDir ++ "/loader.bin")
  let capture ← IO.FS.readBinFile (fixtureDir ++ "/observer.bin")
  for index in [:trials.size] do
    let t := trials[index]!
    let address : UInt64 := 0x100000f8b
    let regs := (List.range 16).toArray.map (fun i => UInt64.ofNat (0x12340000+37*i))
    let regs := (((regs.set! 0 t.rax).set! 1 t.rcx).set! 3 t.rbx).set! 7 (address+113)
    let bytes := ByteArray.mk ((List.range 1024).toArray.map (fun i => UInt8.ofNat (i*17+29)))
    let bytes := putWord bytes 113 0x8877665544332211
    let extra := ByteArray.mk #[18,52,86,120,154]
    let memory : Array Region := #[⟨address,bytes⟩,⟨address+1500,extra⟩,⟨0x200000001,extra⟩]
    let result ← observe loader capture (workDir ++ s!"/trial-{index}.elf")
      { instruction := ByteArray.mk t.instruction, gprs := regs, flags := t.flags, memory := memory }
    let expected := (regs.set! 0 t.expectedRax).set! 1 t.expectedRcx
    let expectedBytes := if t.stores then putWord bytes 113 t.rax else bytes
    let ok := result.gprs == expected &&
      (result.flags &&& t.flagsMask) == (t.expectedFlags &&& t.flagsMask) &&
      result.rip == UInt64.ofNat (target+t.instruction.size) &&
      result.memory.size == 3 && result.memory[0]!.bytes == expectedBytes &&
      result.memory[1]!.bytes == extra && result.memory[2]!.bytes == extra
    IO.println s!"{t.name}: RAX={result.gprs[0]!} RCX={result.gprs[1]!} RFLAGS={result.flags} RIP={result.rip} memory[113]={word result.memory[0]!.bytes 113}"
    if !ok then
      throw <| IO.userError s!"unexpected observation; GPRs={result.gprs}, expected={expected}, expected flags={t.expectedFlags} mask={t.flagsMask}"
    IO.println "  PASS: all 16 GPRs, defined flags, PC, and all 1034 requested memory bytes"
  IO.println "PASS: ten concrete native instruction observations"
