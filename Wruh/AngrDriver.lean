import Wruh.FreshExtraction
import Wruh.FreshTransform
import Ayxg.QfAbv.JsonCodec
import Lean

/-! Executable, Lean-owned fresh extraction over observations supplied by angr. -/
namespace Wruh.AngrDriver

open Lean Ayxg.QfAbv Ayxg.QfAbv.JsonCodec Wruh.Observation Wruh.FreshExtraction

inductive FaultKind where
  | integerDivision
  | invalidOpcode
  deriving DecidableEq, Repr

private def faultKindOfJumpkind (jumpkind : String) : Option FaultKind :=
  if jumpkind == "Ijk_SigFPE_IntDiv" then
    some .integerDivision
  else if jumpkind == "Ijk_SigILL" then
    some .invalidOpcode
  else
    none

example : faultKindOfJumpkind "Ijk_SigFPE_IntDiv" = some .integerDivision := rfl
example : faultKindOfJumpkind "Ijk_SigILL" = some .invalidOpcode := rfl
example : faultKindOfJumpkind "Ijk_NoDecode" = none := rfl

structure Metadata (Γ : Ctx) where
  occurrenceId : Nat
  outcomeId : Nat
  target : Expr Γ (.bv 64)
  targetValue : Option Nat
  jumpkind : String
  kind : OutcomeKind Γ FaultKind

structure Site (Γ : Ctx) where
  address : Nat
  sourceGuard : Expr Γ .bool
  outcomes : List (Outcome Γ (Metadata Γ))

/-- Interpret the outcome-bearing part of an extracted edge label. The label
also retains the complete site and raw angr jumpkind for provenance. -/
def outcomeView [FPInterpretation] (Γ : Ctx) :
    OutcomeView (Site Γ × Metadata Γ) Γ (BitVec 64) FaultKind where
  site edge := BitVec.ofNat 64 edge.1.address
  target edge env := Eval.evalBv env edge.2.target
  targetValue edge := edge.2.targetValue.map (BitVec.ofNat 64)
  kind edge := edge.2.kind

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

private def parseOutcome (Γ : Ctx) (sourceGuard : Expr Γ .bool)
    (occurrenceId : Nat)
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
  let kind : OutcomeKind Γ FaultKind := match faultKindOfJumpkind jumpkind with
    | some faultKind => .fault ⟨faultKind, .boolAnd sourceGuard guard⟩
    | none => .ordinary
  let metadata : Metadata Γ := {
    occurrenceId
    outcomeId
    target
    targetValue
    jumpkind
    kind
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
    (parseOutcome Γ sourceGuard occurrenceId roots)
  pure { address, sourceGuard, outcomes }

/-- Supply fresh tagged successors from angr observations. This operation is
only for canonical input; no arbitrary-input symex claim is made here. -/
def freshSuccessors (Γ : Ctx) (program : List (Site Γ)) :
    List (TaggedSuccessor (Site Γ × Metadata Γ) Γ) :=
  program.flatMap fun site =>
    site.outcomes.map fun outcome =>
      let transformer := Wruh.FreshTransform.transform site.sourceGuard outcome
      { edge := (site, transformer.metadata), step := transformer.step }

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
  let target := match metadata.kind with
    | .fault _ => Json.mkObj [("kind", toJson "error")]
    | .ordinary | .recovery _ => match metadata.targetValue with
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
  let tagged := freshSuccessors Γ sites
  let mut edges := #[]
  for successor in tagged do
    let (site, metadata) := successor.edge
    let transformer : Wruh.FreshTransform.Transformer Γ (Metadata Γ) :=
      ⟨successor.step, metadata⟩
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
