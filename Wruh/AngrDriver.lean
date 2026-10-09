import Wruh.FreshExtraction
import Ayxg.QfAbv.JsonCodec
import Lean

/-! Executable, Lean-owned fresh extraction over observations supplied by angr. -/
namespace Wruh.AngrDriver

open Lean Ayxg.QfAbv Ayxg.QfAbv.JsonCodec Wruh.Observation Wruh.FreshExtraction

structure Metadata (Γ : Ctx) where
  occurrenceId : Nat
  outcomeId : Nat
  target : Expr Γ (.bv 64)
  targetValue : Option Nat
  jumpkind : String

structure Site (Γ : Ctx) where
  address : Nat
  sourceGuard : Expr Γ .bool
  outcomes : List (Outcome Γ (Metadata Γ))

private def root {Γ : Ctx} (roots : Array (TypedExpr Γ)) (index : Nat) :
    Except String (TypedExpr Γ) :=
  match roots[index]? with
  | some value => pure value
  | none => throw "expression root outside DAG"

private def parseUpdate (Γ : Ctx) (roots : Array (TypedExpr Γ)) :
    (Δ : Ctx) → List Nat → Except String (StateUpdate Γ Δ)
  | [], [] => pure .nil
  | declaration :: rest, index :: indices => do
      let value ← asSort declaration.sort (← root roots index)
      pure (.cons value (← parseUpdate Γ roots rest indices))
  | _, _ => throw "complete update has wrong length"

private def parseOutcome (Γ : Ctx) (occurrenceId : Nat)
    (roots : Array (TypedExpr Γ)) (item : Json) :
    Except String (Outcome Γ (Metadata Γ)) := do
  let guard ← asSort .bool (← root roots (← natField item "guard"))
  let indices ← (← field item "updates").getArr?
  let after ← parseUpdate Γ roots Γ (← indices.toList.mapM Json.getNat?)
  let target ← asSort (.bv 64) (← root roots (← natField item "target"))
  let targetValue? ← field item "target_value"
  let targetValue ← if targetValue? == Json.null then pure none else some <$> targetValue?.getNat?
  let outcomeId ← natField item "outcome_id"
  let jumpkind ← (← field item "jumpkind").getStr?
  let metadata : Metadata Γ := {
    occurrenceId
    outcomeId
    target
    targetValue
    jumpkind
  }
  pure {
    temporaryCtx := Γ
    bindings := .nil
    before := StateUpdate.identity Γ
    after
    guard
    metadata
  }

/-- Decode one worker response using AYXG's shared, typed expression DAG reader. -/
def parseSite (Γ : Ctx) (address occurrenceId : Nat) (response : Json) :
    Except String (Site Γ) := do
  let kind ← (← field response "kind").getStr?
  let actualAddress ← natField response "address"
  if kind != "step" || actualAddress != address then
    throw "angr response does not match requested site"
  let roots := (← parseRootsDag Γ (← field response "expression_dag")).toArray
  let sourceGuard ← asSort .bool (← root roots (← natField response "source_guard"))
  let outcomes ← (← (← field response "outcomes").getArr?).toList.mapM
    (parseOutcome Γ occurrenceId roots)
  pure { address, sourceGuard, outcomes }

/-- Only the operational adapter fields are used here. The two source-relation
fields are proof premises for a separate angr correspondence result; this
executable asserts no such result. -/
def adapter (Γ : Ctx) : Adapter (List (Site Γ)) (Site Γ) (Metadata Γ) Γ where
  sites program := program
  emulate _ _ _ := False
  emulateAt _ _ _ _ := False
  input _ site := ⟨site.sourceGuard, StateUpdate.identity Γ⟩
  step _ site _ := site.outcomes

private abbrev RootWriter (Γ : Ctx) := StateM (Array (TypedExpr Γ))

private def addRoot {Γ : Ctx} (expression : TypedExpr Γ) : RootWriter Γ Json := do
  let index := (← get).size
  modify fun roots => roots.push expression
  pure <| Json.mkObj [("$expr", toJson index)]

private def updateJson {Γ : Ctx} : (Δ : Ctx) → StateUpdate Γ Δ →
    RootWriter Γ (List Json)
  | [], .nil => pure []
  | declaration :: rest, .cons value tail => do
      let expression ← addRoot (.mk declaration.sort value)
      let remaining ← updateJson rest tail
      pure <| Json.mkObj [("name", toJson declaration.name), ("value", expression)] :: remaining

private def edgeJson {Γ : Ctx} (address : Nat)
    (transformer : Wruh.FreshTransform.Transformer Γ (Metadata Γ)) :
    RootWriter Γ Json := do
  let step := transformer.step
  let metadata := transformer.metadata
  let guard ← addRoot (.mk .bool step.guard)
  let assignments ← updateJson Γ step.update
  let mirroredPc ← addRoot (.mk (.bv 64) metadata.target)
  let target :=
    if metadata.jumpkind == "Ijk_SigFPE_IntDiv" then
      Json.mkObj [("kind", toJson "error")]
    else match metadata.targetValue with
      | some value => Json.mkObj [("kind", toJson "address"), ("value", toJson value)]
      | none => Json.mkObj [("kind", toJson "symbolic"), ("value", mirroredPc)]
  pure <| Json.mkObj [
    ("edge_id", Json.mkObj [
      ("static_occurrence_id", toJson metadata.occurrenceId),
      ("outcome_id", toJson metadata.outcomeId)]),
    ("source", toJson address),
    ("summary", Json.mkObj [
      ("guard", guard),
      ("simultaneous_update", toJson assignments),
      ("target", target),
      ("mirrored_pc", mirroredPc)])]

/-- The actual WRUH extractor constructs the guarded complete-state edges. -/
def functionJson {Γ : Ctx} (declarations architecture : Json)
    (functionId : String) (entry : Nat) (occurrences : List Json)
    (sites : List (Site Γ)) : RootWriter Γ Json := do
  let tagged := extractTagged (adapter Γ) sites
  let mut edges := #[]
  for (site, transformer) in tagged do
    edges := edges.push (← edgeJson site.address transformer)
  pure <| Json.mkObj [
    ("schema", toJson "ghot-fresh-function-v1"),
    ("function_id", toJson functionId),
    ("entry", toJson entry),
    ("declarations", declarations),
    ("occurrences", toJson occurrences),
    ("local_edges", toJson edges),
    ("architecture", architecture)]

/-- Package all Lean-authored edges in AYXG's existing shared-DAG envelope. -/
def bundleJson {Γ : Ctx} (inventory : Json) (functions : List Json)
    (roots : Array (TypedExpr Γ)) : Except String Json := do
  let imageSha256 ← field inventory "image_sha256"
  let rootId ← field inventory "root_id"
  let cfg ← field inventory "cfg"
  let externalEdges ← field inventory "external_edges"
  let fields := [
    ("schema", toJson "wruh-fresh-bundle-v1"),
    ("image_sha256", imageSha256),
    ("root_id", rootId),
    ("cfg", cfg),
    ("functions", toJson functions),
    ("external_edges", externalEdges)]
  let fields := match (inventory.getObjVal? "loaded_image").toOption with
    | some image => fields ++ [("loaded_image", image)]
    | none => fields
  pure <| Json.mkObj [
    ("schema", toJson "ayxg-artifact-dag-v1"),
    ("expression_dag", writeRootsDag roots.toList),
    ("payload", Json.mkObj fields)]

end Wruh.AngrDriver
