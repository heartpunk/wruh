import GeneratedCase
import ConcreteModel

namespace Wruh.IFormPbt

open Ayxg.QfAbv MovObserver.NativeObserver

/-- Combine generated GPRs, flags, and memory with explicitly supplied values
    for any other modeled input needed by the instruction. -/
def GeneratedCase.modelInput (c : GeneratedCase)
    (otherScalar : String → Option Nat) (otherMemory : Nat → UInt8) : ModelInput :=
  let names := #["rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi",
    "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15"]
  let scalar := fun name => Id.run do
    for i in [:names.size] do
      if names[i]! == name then return c.gprs[i]?.map UInt64.toNat
    for (flag, bit) in #[("CF", 0), ("PF", 2), ("AF", 4), ("ZF", 6), ("SF", 7), ("OF", 11)] do
      if name == "rflags_" ++ flag then return some ((c.flags.toNat / 2^bit) % 2)
    if name == "rip" then return some 0x400170
    if name == "d" then return some (if (c.flags.toNat / 2^10) % 2 == 1 then 2^64-1 else 1)
    if name == "ac" then return some ((c.flags.toNat / 2^18) % 2)
    if name == "id" then return some ((c.flags.toNat / 2^21) % 2)
    return otherScalar name
  let memory := fun address =>
    if address ≥ c.memoryAddress.toNat && address - c.memoryAddress.toNat < c.memoryBytes.size then
      c.memoryBytes[address - c.memoryAddress.toNat]!
    else otherMemory address
  ⟨scalar, memory⟩

inductive CaseResult where
  | matched
  | mismatch (differences : Array String)
  | incomplete (reason : String)
  deriving Repr

/-- Evaluate one extracted model and compare it to one native execution. -/
def GeneratedCase.compare (c : GeneratedCase) (model : ExtractedTarget)
    (otherScalar : String → Option Nat) (otherMemory : Nat → UInt8)
    (loader capture : ByteArray) (workPath : System.FilePath)
    (definedFlags : UInt64) : IO CaseResult := do
  let env ← match inputEnv (c.modelInput otherScalar otherMemory) model.Γ with
    | .ok env => pure env
    | .error reason => return .incomplete reason
  let outcomes := enabledOutcomes model env
  if outcomes.size != 1 then
    return .incomplete s!"expected one enabled model outcome, got {outcomes.size}"
  let native ← observeInstruction loader capture workPath c.observerRequest
  if native.fault.isSome then return .incomplete "native instruction faulted"
  let some (_, post) := outcomes[0]? | return .incomplete "missing model outcome"
  let modelPc ← match readBv post "rip" with
    | .ok pc => pure pc
    | .error reason => return .incomplete reason
  let nativePc := 0x400170 + c.occurrence.bytes.size
  if modelPc != nativePc then
    return .incomplete s!"model target {modelPc} is not fallthrough {nativePc}"
  match compareObserved post native definedFlags with
  | .error reason => return .incomplete reason
  | .ok differences =>
    if differences.isEmpty then return .matched else return .mismatch differences

end Wruh.IFormPbt
