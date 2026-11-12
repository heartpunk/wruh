import Lean
import Ayxg.QfAbv.JsonCodec
import VectorState

namespace Wruh.IFormPbt

open Lean Ayxg.QfAbv.JsonCodec

structure ModelFootprint where
  inputs : Array String
  guardInputs : Array String
  unobservedWrites : Array String
  readsMemory : Bool
  memoryAddresses : Array Nat
  deriving Repr

private def observed (name : String) : Bool :=
  #["rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi",
    "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15",
    "rip", "d", "ac", "id", "rflags_CF", "rflags_PF", "rflags_AF",
    "rflags_ZF", "rflags_SF", "rflags_OF", "mem"].contains name || isVectorField name

private def nodeAt (nodes roots : Array Json) (ref : Json) : Except String (Nat × Json) := do
  let root ← natField ref "$expr"
  let some indexJson := roots[root]? | throw "model root reference out of bounds"
  let index ← indexJson.getNat?
  let some node := nodes[index]? | throw "model node reference out of bounds"
  pure (index, node)

private partial def visit (nodes : Array Json) (index : Nat)
    (seen vars addresses : Array Nat) (readsMemory : Bool) :
    Except String (Array Nat × Array Nat × Array Nat × Bool) := do
  if seen.contains index then return (seen, vars, addresses, readsMemory)
  let some node := nodes[index]? | throw "model expression node out of bounds"
  let op ← (← field node "op").getStr?
  if op == "let_par" then throw "model contains scoped bindings that need dependency analysis"
  let mut seen := seen.push index
  let mut vars := vars
  let mut addresses := addresses
  let mut readsMemory := readsMemory || op == "select"
  if op == "var" then vars := vars.push (← natField node "index")
  let args ← (← field node "args").getArr?
  for arg in args do
    let (nextSeen, nextVars, nextAddresses, nextReads) ←
      visit nodes (← arg.getNat?) seen vars addresses readsMemory
    seen := nextSeen
    vars := nextVars
    addresses := nextAddresses
    readsMemory := nextReads
  if op == "select" || op == "store" then
    let some address := args[1]? | throw "memory operation has no address"
    addresses := addresses.push (← address.getNat?)
  pure (seen, vars, addresses, readsMemory)

/-- Identify model inputs and modeled writes relevant to a single stub site.
    Unknown binding structures are reported as incomplete rather than guessed. -/
def modelFootprint (artifact : Json) (functionId : String) (address : Nat) :
    Except String ModelFootprint := do
  let dag ← field artifact "expression_dag"
  let nodes ← (← field dag "nodes").getArr?
  let roots ← (← field dag "roots").getArr?
  let functions ← (← field (← field artifact "payload") "functions").getArr?
  let some fn := functions.find? (fun f =>
    (field f "function_id" >>= Json.getStr?).toOption == some functionId)
    | throw "fixture function missing from Wruh model"
  let declarations ← (← field fn "declarations").getArr?
  let names ← declarations.mapM (fun d => (field d "name" >>= Json.getStr?))
  let edges ← (← field fn "local_edges").getArr?
  let edges := edges.filter (fun edge => (natField edge "source").toOption == some address)
  if edges.isEmpty then throw "fixture instruction has no Wruh model edges"
  let mut rootsToVisit : Array Nat := #[]
  let mut guardRoots : Array Nat := #[]
  let mut unobservedWrites : Array String := #[]
  for edge in edges do
    let summary ← field edge "summary"
    let (guard, _) ← nodeAt nodes roots (← field summary "guard")
    guardRoots := guardRoots.push guard
    rootsToVisit := rootsToVisit.push guard
    let assignments ← (← field summary "simultaneous_update").getArr?
    if assignments.size != names.size then throw "model update does not match declarations"
    for i in [:assignments.size] do
      let name ← (← field assignments[i]! "name").getStr?
      if names[i]! != name then throw "model update declaration order differs"
      let (index, node) ← nodeAt nodes roots (← field assignments[i]! "value")
      if observed name then
        rootsToVisit := rootsToVisit.push index
      else
        let identity := (field node "op" >>= Json.getStr?).toOption == some "var" &&
          (natField node "index").toOption == some i
        if !identity && !unobservedWrites.contains name then
          unobservedWrites := unobservedWrites.push name
  let mut seen := #[]
  let mut vars := #[]
  let mut addresses := #[]
  let mut readsMemory := false
  for root in rootsToVisit do
    let (s, v, a, r) ← visit nodes root seen vars addresses readsMemory
    seen := s
    vars := v
    addresses := a
    readsMemory := r
  let mut inputs := #[]
  for index in vars do
    let some name := names[index]? | throw "model variable index out of bounds"
    if !inputs.contains name then inputs := inputs.push name
  let mut guardVars := #[]
  let mut guardSeen := #[]
  for root in guardRoots do
    let (s, v, _, _) ← visit nodes root guardSeen guardVars #[] false
    guardSeen := s
    guardVars := v
  let mut guardInputs := #[]
  for index in guardVars do
    let some name := names[index]? | throw "model guard variable index out of bounds"
    if !guardInputs.contains name then guardInputs := guardInputs.push name
  pure ⟨inputs, guardInputs, unobservedWrites, readsMemory, addresses⟩

end Wruh.IFormPbt
