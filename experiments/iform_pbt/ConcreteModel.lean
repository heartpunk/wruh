import Wruh.IFormPbt.ExtractedTarget
import Ayxg.QfAbv.ExecutableFP
import Observer

namespace Wruh.IFormPbt

open Ayxg.QfAbv

local instance : FPInterpretation := FPInterpretation.executableChoice

/-- Concrete input supplied by the same native observation request. Missing
    values are errors so the comparison never silently invents register state. -/
structure ModelInput where
  scalar : String → Option Nat
  memory : Nat → UInt8

def inputValue (input : ModelInput) (d : Decl) : Except String (Denote d.sort) :=
  match d.sort with
  | .bv width => do
      let some value := input.scalar d.name
        | throw s!"no concrete input for {d.name}"
      pure (BitVec.ofNat width value)
  | .array _ width =>
      if d.name == "mem" then
        pure fun address => BitVec.ofNat width (input.memory address.toNat).toNat
      else throw s!"no concrete array input for {d.name}"
  | _ => throw s!"unsupported input sort for {d.name}"

def inputEnv (input : ModelInput) : (Γ : Ctx) → Except String (Env Γ)
  | [] => pure .nil
  | d :: ds => do pure (.cons (← inputValue input d) (← inputEnv input ds))

/-- Evaluate all enabled Wruh outcomes with AYXG's evaluator. -/
def enabledOutcomes (model : ExtractedTarget) (input : Env model.Γ) :
    Array (Nat × Env model.Γ) := Id.run do
  let mut result := #[]
  for edge in model.edges do
    if Eval.evalBool input edge.guard then
      result := result.push (edge.outcomeId, edge.update.eval input)
  return result

/-- Read a named bit-vector from a concrete post-state. -/
def readBv : {Γ : Ctx} → Env Γ → String → Except String Nat
  | [], .nil, name => throw s!"model has no field {name}"
  | d :: _, .cons value rest, name =>
    if d.name == name then
      match h : d.sort with
      | .bv width => pure ((cast (congrArg Denote h) value : BitVec width).toNat)
      | _ => throw s!"model field {name} is not a bit-vector"
    else readBv rest name

/-- Read one byte from the model's post-state memory. -/
def readMemory : {Γ : Ctx} → Env Γ → Nat → Except String Nat
  | [], .nil, _ => throw "model has no memory field"
  | d :: _, .cons value rest, address =>
    if d.name == "mem" then
      match h : d.sort with
      | .array iw vw => pure (((cast (congrArg Denote h) value : Mem iw vw) (BitVec.ofNat iw address)).toNat)
      | _ => throw "model memory is not an array"
    else readMemory rest address

/-- Compare the state fields shared by a model and a native observation.
    The caller supplies the architecture-defined flag mask for the instruction. -/
def compareObserved {Γ : Ctx} (post : Env Γ)
    (native : MovObserver.NativeObserver.Observation) (definedFlags : UInt64) :
    Except String (Array String) := do
  let names := #["rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi",
    "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15"]
  if native.gprs.size != names.size then throw "native GPR capture has wrong length"
  let mut differences := #[]
  for i in [:names.size] do
    let modelValue ← readBv post names[i]!
    let nativeValue := native.gprs[i]!.toNat
    if modelValue != nativeValue then
      differences := differences.push s!"{names[i]!}: model={modelValue}, native={nativeValue}"
  for (name, bit) in #[("CF", 0), ("PF", 2), ("AF", 4), ("ZF", 6), ("SF", 7), ("OF", 11)] do
    if (definedFlags.toNat / 2^bit) % 2 == 1 then
      let modelValue ← readBv post ("rflags_" ++ name)
      let nativeValue := (native.terminalFlags.toNat / 2^bit) % 2
      if modelValue != nativeValue then
        differences := differences.push s!"{name}: model={modelValue}, native={nativeValue}"
  for (name, bit) in #[("d", 10), ("ac", 18), ("id", 21)] do
    let modelValue ← readBv post name
    let flag := (native.terminalFlags.toNat / 2^bit) % 2
    let nativeValue := if name == "d" then (if flag == 1 then 2^64-1 else 1) else flag
    if modelValue != nativeValue then
      differences := differences.push s!"{name}: model={modelValue}, native={nativeValue}"
  for region in native.memory do
    for i in [:region.bytes.size] do
      let address := region.address.toNat + i
      let modelValue ← readMemory post address
      let nativeValue := region.bytes[i]!.toNat
      if modelValue != nativeValue then
        differences := differences.push s!"memory[{address}]: model={modelValue}, native={nativeValue}"
  pure differences

end Wruh.IFormPbt
