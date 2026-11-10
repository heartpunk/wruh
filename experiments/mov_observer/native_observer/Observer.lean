import MemoryWrite
import InstallationEncoding
import FlagsBuffer
namespace MovObserver.NativeObserver
open NativeShim

@[extern "observer_fresh_buffer"] opaque freshBuffer (length : UInt64) : BaseIO ByteArray

@[extern "observer_ptrace"] opaque trace (request pid address data : UInt64) : BaseIO UInt64
@[extern "observer_ptrace_buffer"] opaque traceBuffer (request pid address : UInt64)
  (buffer : @& ByteArray) : BaseIO UInt64
@[extern "observer_wait"] opaque waitRaw (pid : UInt64) (status : @& ByteArray) : BaseIO UInt64
@[extern "observer_kill"] opaque killRaw (pid signal : UInt64) : BaseIO UInt64
@[extern "observer_read_memory"] opaque readRaw (pid address : UInt64)
  (buffer : @& ByteArray) : BaseIO UInt64

-- Transport values only: GPR order matches stub.py and NativeBoundary.imageGprs.
structure Region where
  address : UInt64
  bytes : ByteArray
  deriving Inhabited
structure Request where
  instruction : ByteArray
  gprs : Array UInt64
  flags : UInt64
  memory : Array Region
  fp : Option ByteArray := none
  xstate : Option ByteArray := none
structure TargetFault where
  signal : UInt64
  code : Int
  address : Option UInt64
  rawSiginfo : ByteArray

structure Observation where
  fault : Option TargetFault
  gprs : Array UInt64
  -- GPRs from MOV capture on success, direct stopped registers on fault.
  -- Raw flags/context below belong to the terminal stop in either case.
  terminalFlags : UInt64
  memory : Array Region
  rawTerminalRegisters : ByteArray
  requestedFp : Option ByteArray
  installedFp : ByteArray
  terminalFp : ByteArray
  installedXstate : Option ByteArray
  terminalXstate : Option ByteArray

def zeros (n : Nat) : ByteArray := ByteArray.mk (Array.replicate n 0)
def appendLE (b : ByteArray) (v : Nat) (n : Nat) : ByteArray := Id.run do
  let mut b := b
  for i in [:n] do b := b.push (UInt8.ofNat (v / 2^(8*i)))
  return b

def code : Nat := 0x400000
def loadCode : Nat := 0x400100
def target : Nat := 0x400170
def record : Nat := 0x601040
def input : Nat := 0x601140

def checked (label : String) (call : BaseIO UInt64) : IO UInt64 := do
  let raw ← call
  if raw.toInt64.toInt < 0 then throw <| IO.userError s!"{label}: raw errno {raw.toInt64.toInt}"
  return raw

def getRegisters (pid : UInt64) : IO ByteArray := do
  let buffer ← freshBuffer 216
  let _ ← checked "GETREGS" (traceBuffer 12 pid 0 buffer)
  return buffer

/-- Linux x86-64 user_fpregs_struct, same legacy image as LegacyFp.lean.
Retain all bytes; architectural installation excludes padding and MXCSR_MASK. -/
def getFp (pid : UInt64) : IO ByteArray := do
  let buffer ← freshBuffer 512
  let _ ← checked "GETFPREGS" (traceBuffer 14 pid 0 buffer)
  return buffer

def fpStateByte (i : Nat) : Bool :=
  i < 5 || (6 ≤ i && i < 28) ||
  (32 ≤ i && i < 160 && (i-32)%16 < 10) || (160 ≤ i && i < 416)

def installFp (pid : UInt64) (requested : Option ByteArray) : IO ByteArray := do
  if let some image := requested then
    if image.size != 512 then throw <| IO.userError "FP image must contain 512 bytes"
    let _ ← checked "SETFPREGS" (traceBuffer 15 pid 0 image)
  let installed ← getFp pid
  if let some image := requested then
    for i in [:512] do
      if fpStateByte i && image[i]! != installed[i]! then
        throw <| IO.userError s!"FP installation differs at byte {i}: requested={image[i]!}, installed={installed[i]!}"
  return installed

@[extern "observer_regset"] opaque regset (request pid : UInt64) (buffer : @& ByteArray) : BaseIO UInt64
@[extern "observer_cpuid"] opaque cpuidRaw (leaf subleaf : UInt64) (buffer : @& ByteArray) : BaseIO UInt64
@[extern "observer_xcr0"] opaque xcr0 : BaseIO UInt64

def cpuid (leaf subleaf : UInt64) : IO ByteArray := do
  let b ← freshBuffer 16
  let _ ← cpuidRaw leaf subleaf b
  return b

def dword (b : ByteArray) (i : Nat) : UInt64 := Id.run do
  let mut v : UInt64 := 0
  for j in [:4] do v := v ||| (b[i+j]!.toUInt64 <<< UInt64.ofNat (8*j))
  return v

/-- Standard Linux xstate UABI; offsets come from this CPU, not a fixed XSAVE size. -/
structure VectorLayout where
  bytes : Nat
  enabled : UInt64
  ymm : Nat
  masks : Nat
  zmmHi : Nat
  hi16 : Nat
  deriving Repr

def vectorLayout : IO (Option VectorLayout) := do
  let f ← cpuid 1 0
  if (dword f 8 &&& 0x0c000000) != 0x0c000000 then return none
  let enabled ← xcr0
  let d ← cpuid 13 0
  let mut offsets := #[]
  for component in #[2,5,6,7] do
    let c ← cpuid 13 component
    let size := (dword c 0).toNat
    let offset := (dword c 4).toNat
    if (enabled &&& (1 <<< component)) != 0 && (size == 0 || offset+size > (dword d 4).toNat) then
      throw <| IO.userError "invalid CPUID xstate component extent"
    offsets := offsets.push offset
  return some ⟨(dword d 4).toNat,enabled,offsets[0]!,offsets[1]!,offsets[2]!,offsets[3]!⟩

def getXstate (pid : UInt64) (layout : VectorLayout) : IO ByteArray := do
  let b ← freshBuffer (UInt64.ofNat layout.bytes)
  let n ← checked "GETREGSET xstate" (regset 0x4204 pid b)
  if n.toNat < 576 || n.toNat > b.size then throw <| IO.userError "invalid xstate length"
  let b := b.extract 0 n.toNat
  if word b 520 != 0 then throw <| IO.userError "expected standard xstate layout"
  return b

/-- Canonical vector bytes; absent XSTATE_BV components have architectural zero state. -/
def vectorBytes (layout : VectorLayout) (b : ByteArray) : IO ByteArray := do
  let present := word b 512
  let mut result := ByteArray.empty
  let components : Array (Nat × Nat × Nat) := #[(1,160,256),(2,layout.ymm,256),
    (5,layout.masks,64),(6,layout.zmmHi,512),(7,layout.hi16,1024)]
  for (bit,offset,size) in components do
    if (layout.enabled &&& (1 <<< UInt64.ofNat bit)) != 0 then
      if offset+size > b.size then throw <| IO.userError "truncated vector component"
      result := result ++ (if (present &&& (1 <<< UInt64.ofNat bit)) == 0 then zeros size else b.extract offset (offset+size))
  return result

def installXstate (pid : UInt64) (layout : VectorLayout) (requested : Option ByteArray) : IO ByteArray := do
  if let some b := requested then
    let before ← getXstate pid layout
    if b.size != before.size || word b 520 != 0 then throw <| IO.userError "invalid requested standard xstate image"
    let n ← checked "SETREGSET xstate" (regset 0x4205 pid b)
    if n.toNat != b.size then throw <| IO.userError "short xstate installation"
  let installed ← getXstate pid layout
  if let some b := requested then
    if (← vectorBytes layout b) != (← vectorBytes layout installed) then throw <| IO.userError "vector installation differs"
  return installed

def readMemory (pid address : UInt64) (length : Nat) : IO ByteArray := do
  let buffer ← freshBuffer (UInt64.ofNat length)
  let n ← checked "read memory" (readRaw pid address buffer)
  if n.toNat != length then throw <| IO.userError s!"short read {n}/{length}"
  return buffer

def writeMemory (pid address : UInt64) (bytes : ByteArray) : IO Unit := do
  let n ← checked "write memory" (writeMemoryOnce pid.toUInt32 address bytes)
  if n.toNat != bytes.size then throw <| IO.userError s!"short write {n}/{bytes.size}"

structure NativeStop where
  signal : UInt64
  regs : ByteArray
  info : ByteArray

def waitStop (pid : UInt64) : IO NativeStop := do
  let status ← freshBuffer 8
  let got ← checked "wait4" (waitRaw pid status)
  let s := word status 0
  if got != pid || (s &&& 255) != 127 then
    throw <| IO.userError s!"unexpected process outcome: pid={got}, status={s}"
  let regs ← getRegisters pid
  let info ← freshBuffer 128
  let _ ← checked "GETSIGINFO" (traceBuffer 0x4202 pid 0 info)
  return ⟨(s >>> 8) &&& 255,regs,info⟩

def isMarker (stop : NativeStop) (rip : UInt64) : Bool :=
  let reason := dword stop.info 8
  stop.signal == 5 && word stop.regs (16*8) == rip && (reason == 1 || reason == 128)

/-- Accept only our designated INT3, not an arbitrary target trap. -/
def stoppedAt (pid expectedRip : UInt64) : IO ByteArray := do
  let stop ← waitStop pid
  if !isMarker stop expectedRip then
    throw <| IO.userError s!"not the designated INT3: signal={stop.signal}, RIP={word stop.regs (16*8)}, code={dword stop.info 8}"
  return stop.regs

/-- user_regs_struct order to the existing loader/capture GPR order. -/
def stoppedGprs (regs : ByteArray) : Array UInt64 :=
  #[10,11,12,5,19,4,13,14,9,8,7,6,3,2,1,0].map (fun i => word regs (8*i))

/-- Positive kernel-generated synchronous fault, stopped at the target instruction.
External signals, asynchronous BUS_MCEERR_AO, and faults in setup/capture are
not target observations. SI_KERNEL has no guaranteed address field. -/
def targetFault (stop : NativeStop) : Option TargetFault :=
  let reason := dword stop.info 8
  if #[4,7,8,11].contains stop.signal && reason > 0 && reason < 0x80000000 &&
      !(stop.signal == 7 && reason == 5) &&
      word stop.regs (16*8) == UInt64.ofNat target then
    some ⟨stop.signal,reason.toNat,(if reason == 128 then none else some (word stop.info 16)),stop.info⟩
  else none

-- Reuse exact committed MOV fragments. ELF maps all requested finite ranges;
-- bytes are installed via the existing memory-write shim after the child stops.
def makeElf (loader capture : ByteArray) (r : Request) : IO ByteArray := do
  if r.gprs.size != 16 || r.instruction.size == 0 || r.instruction.size > 15 then
    throw <| IO.userError "expected sixteen GPRs and one 1–15-byte instruction"
  if loader.size != 112 || capture.size != 112 then
    throw <| IO.userError "expected the existing sixteen-MOV fixtures"
  let mut pages : Array (Nat × Nat) := #[(0x600000, 0x3000)]
  for i in [:r.memory.size] do
    let a := r.memory[i]!.address.toNat
    let n := r.memory[i]!.bytes.size
    if a+n > 2^64 then throw <| IO.userError "memory range wraps"
    if n > 0 then
      let lo := a / 4096 * 4096
      let hi := (a+n+4095) / 4096 * 4096
      if (lo < 0x401000 && 0x400000 < hi) || (lo < 0x603000 && 0x600000 < hi) then
        throw <| IO.userError "requested memory overlaps reserved harness mappings"
      for j in [:i] do
        let b := r.memory[j]!.address.toNat
        let m := r.memory[j]!.bytes.size
        if m > 0 && a < b+m && b < a+n then throw <| IO.userError "overlapping sparse ranges"
      -- Union page mappings, allowing distinct requested ranges on the same page.
      let mut low := lo
      let mut high := hi
      let mut keep := #[]
      for (base, size) in pages do
        if low <= base+size && base <= high then
          low := min low base; high := max high (base+size)
        else keep := keep.push (base,size)
      pages := keep.push (low,high-low)
  let count := pages.size+1
  if count*56 > 65536 then throw <| IO.userError "sparse image exceeds Linux ELF program-header limit"
  let textOffset := ((64+56*count+4095)/4096)*4096
  let mut h := ByteArray.mk #[0x7f,0x45,0x4c,0x46,2,1,1,0,0,0,0,0,0,0,0,0]
  for (v,n) in #[(2,2),(62,2),(1,4),(0x400200,8),(64,8),(0,8),(0,4),(64,2),(56,2),(count,2),(0,2),(0,2),(0,2)] do
    h := appendLE h v n
  for (base,size,offset,fileSize,flags) in (#[(code,4096,textOffset,4096,5)] ++ pages.map (fun (a,n) => (a,n,0,0,6))) do
    for (v,n) in #[(1,4),(flags,4),(offset,8),(base,8),(base,8),(fileSize,8),(size,8),(4096,8)] do
      h := appendLE h v n
  h := h ++ zeros (textOffset-h.size)
  let mut text := zeros 4096
  for i in [:capture.size] do text := text.set! i capture[i]!
  for i in [:loader.size] do text := text.set! (0x100+i) loader[i]!
  for i in [:r.instruction.size] do text := text.set! (0x170+i) r.instruction[i]!
  -- Capture stays at its original address: preserve its RIP-relative stores.
  -- The target falls through to a flag/GPR-neutral relative JMP into capture.
  let continuation := 0x170+r.instruction.size
  let jump := appendLE (ByteArray.mk #[0xe9]) (2^32-(continuation+5)) 4
  for i in [:jump.size] do text := text.set! (continuation+i) jump[i]!
  text := text.set! capture.size 0xcc
  -- TRACEME then INT3, no user stack dependence. Failure exits 127.
  let init := ByteArray.mk #[0x31,0xff,0x31,0xf6,0x31,0xd2,0x45,0x31,0xd2,
    0xb8,101,0,0,0,0x0f,0x05,0x48,0x85,0xc0,0x75,1,0xcc,
    0xbf,127,0,0,0,0xb8,60,0,0,0,0x0f,0x05]
  for i in [:init.size] do text := text.set! (0x200+i) init[i]!
  return h ++ text

/-- Natural execution for a target selected to complete by fallthrough.
The caller supplies one fallthrough instruction; this function does not establish
branch outcomes. Synchronous faults at its PC return the actual stopped state.
Raw terminal context is retained, not relabeled as the original target PC/flags.
No single-stepping, model execution, or differential semantics occurs here. -/
def observeInstruction (loader capture : ByteArray) (path : System.FilePath) (r : Request) : IO Observation := do
  if r.fp.isSome && r.xstate.isSome then throw <| IO.userError "supply either legacy FP or full xstate, not both"
  let layout ← vectorLayout
  if r.xstate.isSome && layout.isNone then throw <| IO.userError "xstate unavailable on this CPU"
  IO.FS.writeBinFile path (← makeElf loader capture r)
  try
    let chmod ← IO.Process.output {cmd := "chmod", args := #["700",path.toString]}
    if chmod.exitCode != 0 then throw <| IO.userError chmod.stderr
    let child ← IO.Process.spawn {cmd := path.toString}
    let pid := UInt64.ofNat child.pid.toNat
    try
      let _ ← stoppedAt pid 0x400216
      let _ ← checked "EXITKILL" (trace 0x4200 pid 0 0x100000)
      for region in r.memory do writeMemory pid region.address region.bytes
      writeMemory pid (UInt64.ofNat input) (encodeGprs r.gprs)
      let regs ← getRegisters pid
      let regs := putWord (writeFlagsWord (putWord regs (16*8) (UInt64.ofNat loadCode)) r.flags) (15*8) 0xffffffffffffffff
      let _ ← checked "SETREGS" (traceBuffer 13 pid 0 regs)
      let installed ← getRegisters pid
      if word installed (16*8) != UInt64.ofNat loadCode || readFlagsWord installed != r.flags then
        throw <| IO.userError "loader entry PC or requested flags not installed"
      let _ ← installFp pid r.fp
      let installedXstate ← match layout with
        | some l => some <$> installXstate pid l r.xstate
        | none => pure none
      let installedFp ← getFp pid
      -- Loader, target, JMP, and MOV capture run without debugger-injected TF.
      let _ ← checked "CONT" (trace 7 pid 0 0)
      let stop ← waitStop pid
      let fault ← if isMarker stop (UInt64.ofNat (code+capture.size+1)) then pure none
        else match targetFault stop with
          | some f => pure (some f)
          | none => throw <| IO.userError s!"unexpected stop outside supported target outcome: signal={stop.signal}, RIP={word stop.regs (16*8)}, code={dword stop.info 8}"
      let terminal := stop.regs
      let terminalXstate ← match layout with
        | some l => some <$> getXstate pid l
        | none => pure none
      let terminalFp ← getFp pid
      let gprs ← if fault.isSome then pure (stoppedGprs terminal) else do
        let data ← readMemory pid (UInt64.ofNat record) 128
        pure ((List.range 16).toArray.map (fun i => word data (8*i)))
      let mut memory := #[]
      for region in r.memory do
        memory := memory.push {region with bytes := ← readMemory pid region.address region.bytes.size}
      return ⟨fault,gprs,
        readFlagsWord terminal, memory, terminal, r.fp, installedFp, terminalFp, installedXstate, terminalXstate⟩
    finally
      let killed ← killRaw pid 9
      let status ← freshBuffer 8
      let reaped ← waitRaw pid status
      if killed.toInt64.toInt < 0 || reaped != pid || (word status 0 &&& 255) == 127 then
        throw <| IO.userError s!"child cleanup failed: kill={killed.toInt64.toInt}, wait={reaped.toInt64.toInt}"
  finally
    IO.FS.removeFile path
/-- Compatibility entry point for callers expecting successful fallthrough only. -/
def observeFallthrough (loader capture : ByteArray) (path : System.FilePath) (r : Request) : IO Observation := do
  let result ← observeInstruction loader capture path r
  if let some f := result.fault then
    throw <| IO.userError s!"target fault: signal={f.signal}, code={f.code}, address={repr f.address}"
  return result
end MovObserver.NativeObserver
