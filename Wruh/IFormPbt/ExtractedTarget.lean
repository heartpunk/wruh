import Ayxg.QfAbv.JsonCodec
import Lean

/-! Read the existing Wruh fresh-extraction artifact as a typed single-site model. -/
namespace Wruh.IFormPbt

open Lean Ayxg.QfAbv Ayxg.QfAbv.JsonCodec

structure ExtractedEdge (Γ : Ctx) where
  source : Nat
  staticOccurrenceId : Nat
  outcomeId : Nat
  guard : Expr Γ .bool
  update : StateUpdate Γ Γ
  target : Expr Γ (.bv 64)
  targetKind : String
  targetValue : Option Nat
  jumpkind : String

structure ExtractedTarget where
  Γ : Ctx
  instructionBytes : ByteArray
  edges : Array (ExtractedEdge Γ)

private def hexDigit (c : Char) : Except String Nat :=
  if '0' ≤ c && c ≤ '9' then pure (c.toNat - '0'.toNat)
  else if 'a' ≤ c && c ≤ 'f' then pure (10 + c.toNat - 'a'.toNat)
  else if 'A' ≤ c && c ≤ 'F' then pure (10 + c.toNat - 'A'.toNat)
  else throw s!"invalid hex digit {c}"

private def decodeHex (text : String) : Except String ByteArray := do
  let chars := text.toList.toArray
  if chars.isEmpty || chars.size % 2 != 0 then
    throw "instruction bytes must be nonempty even-length hex"
  let mut bytes := ByteArray.empty
  for i in [:chars.size / 2] do
    let hi ← hexDigit chars[2*i]!
    let lo ← hexDigit chars[2*i+1]!
    bytes := bytes.push (UInt8.ofNat (hi * 16 + lo))
  pure bytes

private def expressionRef {Γ : Ctx} (roots : Array (TypedExpr Γ))
    (reference : Json) : Except String (TypedExpr Γ) := do
  let index ← natField reference "$expr"
  match roots[index]? with
  | some expression => pure expression
  | none => throw "artifact expression reference outside shared DAG"

private def parseUpdate {Γ : Ctx} (roots : Array (TypedExpr Γ)) :
    (context : Ctx) → List Json → Except String (StateUpdate Γ context)
  | [], [] => pure .nil
  | declaration :: rest, assignment :: assignments => do
      let name ← (← field assignment "name").getStr?
      if name != declaration.name then
        throw s!"artifact assignment {name} is out of declaration order; expected {declaration.name}"
      let value ← asSort declaration.sort
        (← expressionRef roots (← field assignment "value"))
      pure (.cons value (← parseUpdate roots rest assignments))
  | _, _ => throw "artifact simultaneous update does not cover its complete declaration context"

private def parseEdge {Γ : Ctx} (roots : Array (TypedExpr Γ))
    (source : Nat) (edge : Json) : Except String (ExtractedEdge Γ) := do
  let edgeId ← field edge "edge_id"
  let staticOccurrenceId ← natField edgeId "static_occurrence_id"
  let outcomeId ← natField edgeId "outcome_id"
  let summary ← field edge "summary"
  let .mk .bool guard ← expressionRef roots (← field summary "guard")
    | throw "artifact guard is not Boolean"
  let assignmentJson ← (← field summary "simultaneous_update").getArr?
  let update ← parseUpdate roots Γ assignmentJson.toList
  let .mk (.bv 64) target ← expressionRef roots (← field summary "mirrored_pc")
    | throw "artifact next PC is not a 64-bit bitvector"
  let targetDescription ← field summary "target"
  let targetKind ← (← field targetDescription "kind").getStr?
  let targetValue ← match targetDescription.getObjVal? "value" with
    | .ok value => if value == Json.null then pure none else some <$> value.getNat?
    | .error _ => pure none
  let jumpkind ← match edge.getObjVal? "jumpkind" with
    | .ok value => value.getStr?
    | .error _ => pure ""
  pure {
    source := source
    staticOccurrenceId := staticOccurrenceId
    outcomeId := outcomeId
    guard := guard
    update := update
    target := target
    targetKind := targetKind
    targetValue := targetValue
    jumpkind := jumpkind
  }

private def parseOccurrenceIdentity (occurrence : Json) :
    Except String (Nat × Nat × ByteArray) := do
  let staticOccurrenceId ← natField occurrence "static_occurrence_id"
  let origin ← field occurrence "origin"
  let address ← natField origin "canonical_address"
  let bytes ← decodeHex (← (← field origin "instruction_bytes").getStr?)
  pure (staticOccurrenceId, address, bytes)

/-- Decode the emitted `ayxg-artifact-dag-v1` bundle produced by `wruh-fresh`.
The selected edge must belong to the requested function occurrence and carry
the exact instruction bytes requested by the catalogue. -/
def readExtractedTarget (artifact : Json) (functionId : String)
    (requestedBytes : ByteArray) : Except String ExtractedTarget := do
  let schema ← (← field artifact "schema").getStr?
  if schema != "ayxg-artifact-dag-v1" then
    throw s!"unsupported artifact schema {schema}"
  let payload ← field artifact "payload"
  let payloadSchema ← (← field payload "schema").getStr?
  if payloadSchema != "wruh-fresh-bundle-v1" then
    throw s!"unsupported Wruh payload schema {payloadSchema}"
  let functions ← (← field payload "functions").getArr?
  let function ← match functions.find? (fun value =>
      (value.getObjVal? "function_id" >>= Json.getStr?).toOption == some functionId) with
    | some value => pure value
    | none => throw s!"artifact has no function {functionId}"
  let declarationRecords ← (← field function "declarations").getArr?
  let context ← declarationRecords.toList.mapM parseDecl
  let roots := (← parseRootsDag context (← field artifact "expression_dag")).toArray
  let occurrences ← (← field function "occurrences").getArr?
  let identities ← occurrences.toList.mapM parseOccurrenceIdentity
  let matchingOccurrences := identities.filter fun (_, _, bytes) => bytes == requestedBytes
  let (staticOccurrenceId, source, instructionBytes) ← match matchingOccurrences with
    | [identity] => pure identity
    | [] => throw "artifact contains no occurrence with the requested exact bytes"
    | _ => throw "artifact contains multiple occurrences with the requested exact bytes"
  let edges ← (← field function "local_edges").getArr?
  let matching := edges.filter fun edge =>
    (natField edge "source").toOption == some source &&
    ((field edge "edge_id" >>= fun edgeId => natField edgeId "static_occurrence_id").toOption
      == some staticOccurrenceId)
  if matching.isEmpty then throw "artifact has no transformed edges for the requested exact occurrence"
  let parsed ← matching.mapM (parseEdge roots source)
  pure { Γ := context, instructionBytes, edges := parsed }

end Wruh.IFormPbt
