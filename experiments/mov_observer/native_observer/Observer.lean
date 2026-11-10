import MemoryWrite
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
structure Observation where
  gprs : Array UInt64
  flags : UInt64
  rip : UInt64
  memory : Array Region
  rawRegisters : ByteArray

def zeros (n : Nat) : ByteArray := ByteArray.mk (Array.replicate n 0)
def word (b : ByteArray) (offset : Nat) : UInt64 := Id.run do
  let mut v : UInt64 := 0
  for i in [:8] do v := v ||| ((b[offset+i]!).toUInt64 <<< UInt64.ofNat (8*i))
  return v
def putWord (b : ByteArray) (offset : Nat) (v : UInt64) : ByteArray := Id.run do
  let mut b := b
  for i in [:8] do b := b.set! (offset+i) (v >>> UInt64.ofNat (8*i)).toUInt8
  return b
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

def readMemory (pid address : UInt64) (length : Nat) : IO ByteArray := do
  let buffer ← freshBuffer (UInt64.ofNat length)
  let n ← checked "read memory" (readRaw pid address buffer)
  if n.toNat != length then throw <| IO.userError s!"short read {n}/{length}"
  return buffer

def writeMemory (pid address : UInt64) (bytes : ByteArray) : IO Unit := do
  let n ← checked "write memory" (writeMemoryOnce pid.toUInt32 address bytes)
  if n.toNat != bytes.size then throw <| IO.userError s!"short write {n}/{bytes.size}"

def stopped (pid : UInt64) (singleStep : Bool) : IO Unit := do
  let status ← freshBuffer 8
  let got ← checked "wait4" (waitRaw pid status)
  let s := word status 0
  if got != pid || (s &&& 255) != 127 || ((s >>> 8) &&& 255) != 5 then
    throw <| IO.userError s!"target did not reach expected SIGTRAP stop: pid={got}, status={s}"
  if singleStep then
    let info ← freshBuffer 128
    let _ ← checked "GETSIGINFO" (traceBuffer 0x4202 pid 0 info)
    if (word info 8 &&& 0xffffffff) != 2 then
      throw <| IO.userError "target stop was not TRAP_TRACE"

def step (pid : UInt64) : IO Unit := do
  let _ ← checked "SINGLESTEP" (trace 9 pid 0 0)
  stopped pid true

-- Reuse exact committed MOV fragments. ELF maps all requested finite ranges;
-- bytes are installed via the existing memory-write shim after the child stops.
def makeElf (loader capture : ByteArray) (r : Request) : IO ByteArray := do
  if r.gprs.size != 16 || r.instruction.size == 0 || r.instruction.size > 15 then
    throw <| IO.userError "expected sixteen GPRs and one 1–15-byte instruction"
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
  -- TRACEME then INT3, no user stack dependence. Failure exits 127.
  let init := ByteArray.mk #[0x31,0xff,0x31,0xf6,0x31,0xd2,0x45,0x31,0xd2,
    0xb8,101,0,0,0,0x0f,0x05,0x48,0x85,0xc0,0x75,1,0xcc,
    0xbf,127,0,0,0,0xb8,60,0,0,0,0x0f,0x05]
  for i in [:init.size] do text := text.set! (0x200+i) init[i]!
  return h ++ text

/-- One concrete observation. No model execution or differential semantics here.
Unexpected stops/errors abort; detailed fault outcomes are a later stage. -/
def observe (loader capture : ByteArray) (path : System.FilePath) (r : Request) : IO Observation := do
  IO.FS.writeBinFile path (← makeElf loader capture r)
  let chmod ← IO.Process.output {cmd := "chmod", args := #["700",path.toString]}
  if chmod.exitCode != 0 then throw <| IO.userError chmod.stderr
  let child ← IO.Process.spawn {cmd := path.toString}
  let pid := UInt64.ofNat child.pid.toNat
  try
    stopped pid false
    let _ ← checked "EXITKILL" (trace 0x4200 pid 0 0x100000)
    for region in r.memory do writeMemory pid region.address region.bytes
    let mut inputs := zeros 128
    for i in [:16] do inputs := putWord inputs (8*i) r.gprs[i]!
    writeMemory pid (UInt64.ofNat input) inputs
    let regs ← getRegisters pid
    let regs := putWord (putWord (putWord regs (16*8) (UInt64.ofNat loadCode)) (18*8) r.flags) (15*8) 0xffffffffffffffff
    let _ ← checked "SETREGS" (traceBuffer 13 pid 0 regs)
    for _ in [:16] do step pid
    let installed ← getRegisters pid
    let slots := #[10,11,12,5,19,4,13,14,9,8,7,6,3,2,1,0]
    for i in [:16] do
      if word installed (8*slots[i]!) != r.gprs[i]! then throw <| IO.userError s!"GPR {i} was not installed"
    if word installed (16*8) != UInt64.ofNat target || word installed (18*8) != r.flags then
      throw <| IO.userError "entry PC or requested flags not installed"
    step pid
    let post ← getRegisters pid
    let redirected := putWord post (16*8) (UInt64.ofNat code)
    let _ ← checked "capture entry" (traceBuffer 13 pid 0 redirected)
    for _ in [:16] do step pid
    let data ← readMemory pid (UInt64.ofNat record) 128
    let mut memory := #[]
    for region in r.memory do
      memory := memory.push {region with bytes := ← readMemory pid region.address region.bytes.size}
    return ⟨(List.range 16).toArray.map (fun i => word data (8*i)),
      word post (18*8), word post (16*8), memory, post⟩
  finally
    let _ ← killRaw pid 9
    let status ← freshBuffer 8
    let _ ← waitRaw pid status
    IO.FS.removeFile path
end MovObserver.NativeObserver
