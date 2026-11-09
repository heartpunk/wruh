import Protocol

namespace MovObserver.Bootstrap
open Ayxg.QfAbv
variable [FPInterpretation]

/-- Actual AYXG semantics, not effect labels. A basis member may already be an
extracted fragment; expanding it into individual forms is a separate equality
proof, not a claim made by this type. Byte/native linkage remains explicit below. -/
structure Basis (Δ : Ctx) (m : Nat) where
  model : Fin m → QFAbvStep Δ Δ

/-- Finite composition using AYXG's existing semantic operator. This is a proof
term describing the selected fragments, not a new runtime interpreter. -/
def compose {Δ : Ctx} {m : Nat} (basis : Basis Δ m) :
    List (Fin m) → QFAbvStep Δ Δ
  | [] => QFAbvStep.identity Δ
  | i :: rest => (basis.model i).compose (compose basis rest)

/-- The intended profile is fixed independently of the proposed construction.
Views may overlap: they are functions of the same underlying AYXG environment.
`entry` states the actual intended input boundary, including memory/layout;
matching a selected register list alone is not target-state equivalence.
Frames constrain concrete state pairs, not a second instruction semantics. -/
structure Profile (Δ : Ctx) (Value : Type) where
  admitted : Env Δ → Env Δ → Prop
  entry : Env Δ → Env Δ → Env Δ → Prop
  observe : Env Δ → Value
  installFrame : Env Δ → Env Δ → Env Δ → Prop
  captureFrame : Env Δ → Env Δ → Prop

/-- Data only. Preparation/handoff are existing supervisor operations whose
native implementations need their own refinement. They are not silently
counted among the instruction forms in `basis`. Decoding receives the record
memory, never the entire final environment or a direct register oracle. -/
structure Construction (Δ : Ctx) (m : Nat) (Value : Type) where
  basis : Basis Δ m
  install : List (Fin m)
  capture : List (Fin m)
  prepare : Env Δ → Env Δ → Env Δ
  handoff : Env Δ → Env Δ
  addressWidth : Nat
  memory : Var Δ (.array addressWidth 8)
  decode : Mem addressWidth 8 → Value

/-- Local laws are propositions about the actual composed AYXG transitions.
Proving these laws must establish guards as well as value/frame properties.
StageCorrect supplies enabled execution and all-result correctness; native
termination and intermediate-prefix recovery are NOT implied by it. -/
def ComponentObligations {Δ : Ctx} {m : Nat} {Value : Type}
    (p : Profile Δ Value) (c : Construction Δ m Value) : Prop :=
  (∀ wanted ambient, p.admitted wanted ambient →
    StageCorrect (compose c.basis c.install).denotes
      (fun s => s = c.prepare wanted ambient)
      (fun _ loaded => p.entry wanted ambient loaded ∧
        p.installFrame wanted ambient loaded)) ∧
  StageCorrect (fun post final =>
      (compose c.basis c.capture).denotes (c.handoff post) final)
    (fun _ => True)
    (fun post final => c.decode (Env.lookup final c.memory) = p.observe post ∧ p.captureFrame post final)

/-- One target occurrence, opaque to the basis. In particular, T need not be
an AYXG model and no semantic correctness claim about the target is assumed.
The SAME original post-state and event feed capture and its reported value. -/
structure Run {Δ : Ctx} {m : Nat} {Value Event : Type}
    (c : Construction Δ m Value) (T : Env Δ → Event → Env Δ → Prop)
    (wanted ambient : Env Δ) (event : Event) (loaded post final : Env Δ) : Prop where
  installed : (compose c.basis c.install).denotes (c.prepare wanted ambient) loaded
  target : T loaded event post
  captured : (compose c.basis c.capture).denotes (c.handoff post) final

/-- The semantic bootstrap goal. Soundness ranges over every target relation
and every run. Availability requires capture of EVERY target successor, not
only those agreeing with a predicted target model. Original event metadata is
carried unchanged, rather than inferred from the capture fragment's outcome.
This is the completed-stage semantic obligation; it is deliberately not named
native e2e correctness. Native linkage, prefix recovery and actual execution
termination remain separate obligations in the existing observer specification. -/
def BootstrapObligation {Δ : Ctx} {m : Nat} {Value : Type}
    (p : Profile Δ Value) (c : Construction Δ m Value) : Prop :=
  ∀ wanted ambient, p.admitted wanted ambient →
    (∃ loaded, (compose c.basis c.install).denotes
      (c.prepare wanted ambient) loaded) ∧
    (∀ (Event : Type) (T : Env Δ → Event → Env Δ → Prop)
      event loaded post final, Run c T wanted ambient event loaded post final →
      p.entry wanted ambient loaded ∧ p.installFrame wanted ambient loaded ∧
      (event, c.decode (Env.lookup final c.memory)) = (event, p.observe post) ∧
      p.captureFrame post final) ∧
    (∀ (Event : Type) (T : Env Δ → Event → Env Δ → Prop)
      event loaded post,
      (compose c.basis c.install).denotes (c.prepare wanted ambient) loaded →
      T loaded event post → ∃ final, Run c T wanted ambient event loaded post final)

/-- The reusable theorem obligation. A future proof should only use AYXG
composition and ComponentObligations; it must not inspect or execute T. -/
def CompositionTheorem : Prop :=
  ∀ (Δ : Ctx) (m : Nat) (Value : Type)
    (p : Profile Δ Value) (c : Construction Δ m Value),
    ComponentObligations p c → BootstrapObligation p c

/-- Existing MOV fragments: two ALREADY COMPOSED 16-instruction models, not a
claim that two arbitrary iforms have been generalized to every operand layout.
Source bytes are fixtures/loader.bin and fixtures/observer.bin respectively. -/
def movBasis : Basis Γ 2 where
  model i := if i.val = 0 then loadStep else captureStep

def movConstruction : Construction Γ 2 (List (BitVec 64)) where
  basis := movBasis
  install := [0]
  capture := [1]
  prepare := prepareInput
  handoff := enterCapture
  addressWidth := 64
  memory := v_mem
  decode := decodeRecord

/-- Concrete current GPR endpoint scope. The input bytes have their specified
values as well as a frame outside them. This does not assert arbitrary target
independence from private slots, or complete FP/vector/native-state coverage. -/
def movProfile : Profile Γ (List (BitVec 64)) where
  admitted _ _ := True
  entry wanted ambient loaded :=
    observeGprs loaded = observeGprs wanted ∧
    Env.lookup loaded v_rip = BitVec.ofNat 64 0x400170 ∧
    Env.lookup loaded v_mem = prepareInputMemory wanted (Env.lookup ambient v_mem)
  observe := observeGprs
  installFrame _ ambient loaded :=
    StateFrame inputChangedFields (inputWrites.map Prod.fst) ambient loaded
  captureFrame post final :=
    StateFrame captureChangedFields (expectedWrites.map Prod.fst) post final

def MovComponentObligations : Prop := ComponentObligations movProfile movConstruction
def MovBootstrapObligation : Prop := BootstrapObligation movProfile movConstruction

end MovObserver.Bootstrap
