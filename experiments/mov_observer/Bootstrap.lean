import Protocol

namespace MovObserver.Bootstrap
open Ayxg.QfAbv
variable [FPInterpretation]

/- Minimal compatibility definitions reused from UFDA's standalone docs listing:
ufda 8ef1a02d42cbaf4e2831f7f46fd7a87603d7669f,
docs/roadmap/compatibility.md: Rel, RelLe, RelGalois. Kept local because that
listing is not an importable dependency. No UFDA source or dependency changed. -/
namespace Compatibility
universe u v

def Rel (S : Type u) : Type u := S → S → Prop

def RelLe {S : Type u} (R Q : Rel S) : Prop :=
  ∀ s s', R s s' → Q s s'

structure RelGalois (C : Type u) (A : Type v) where
  α : Rel C → Rel A
  γ : Rel A → Rel C
  gc : ∀ (R : Rel C) (Q : Rel A), RelLe (α R) Q ↔ RelLe R (γ Q)

end Compatibility

/-- The only permitted information loss is the caller's explicit state quotient.
Unlike an arbitrary abstraction, this boundary is constructed from that Setoid.
It projects BOTH ends of a behavior relation and uses UFDA's exact Galois law. -/
def quotientBoundary {S : Type} (q : Setoid S) :
    Compatibility.RelGalois S (Quotient q) where
  α R a b := ∃ s t, Quotient.mk q s = a ∧ Quotient.mk q t = b ∧ R s t
  γ Q s t := Q (Quotient.mk q s) (Quotient.mk q t)
  gc R Q := by
    constructor
    · intro h s t hst
      exact h _ _ ⟨s, t, rfl, rfl, hst⟩
    · intro h a b hab
      obtain ⟨s, t, rfl, rfl, hst⟩ := hab
      exact h s t hst

/-- Actual AYXG semantics, not effect labels. A basis member may already be an
extracted fragment; expanding it into individual forms is a separate equality
proof, not a claim made by this type. Concrete byte/native linkage is a
separate existing observer obligation, not discharged by this endpoint statement. -/
structure Basis (Δ : Ctx) (m : Nat) where
  model : Fin m → QFAbvStep Δ Δ

/-- Finite composition using AYXG's existing semantic operator. This is a proof
term describing the selected fragments, not a new runtime interpreter. -/
def compose {Δ : Ctx} {m : Nat} (basis : Basis Δ m) :
    List (Fin m) → QFAbvStep Δ Δ
  | [] => QFAbvStep.identity Δ
  | i :: rest => (basis.model i).compose (compose basis rest)

/-- A typed view of arbitrary modeled state, including overlapping register or
memory views. This is not an independently stored copy of that state. -/
structure StateView (Δ : Ctx) where
  Value : Type
  read : Env Δ → Value

/-- A fixed installation-boundary value, such as entry PC or initialized
private memory. Unlike an arbitrary predicate, this requires a concrete view
value. Requested input views are checked separately against `wanted` itself. -/
structure BoundaryValue (Δ : Ctx) where
  destination : StateView Δ
  value : Env Δ → Env Δ → destination.Value

/-- The intended profile is fixed independently of the proposed construction.
Views may overlap: they are functions of the same underlying AYXG environment.
Requested input views and concrete boundary values specify installation;
matching a selected register list alone is not target-state equivalence.
The caller fixes Δ and q BEFORE choosing a construction. Frames constrain
concrete state pairs, not a second instruction semantics. quotientBoundary q
is the associated UFDA-compatible abstraction of behavior relations. -/
structure Profile (Δ : Ctx) (q : Setoid (Env Δ)) (Value : Type) where
  inputViews : List (StateView Δ)
  boundaryValues : List (BoundaryValue Δ)
  observe : Env Δ → Value
  recover : Value → Option (Quotient q)
  installFrame : Env Δ → Env Δ → Env Δ → Prop
  captureFrame : Env Δ → Env Δ → Prop

/-- The requested views must equal their values in `wanted`; additional
boundary views must equal the profile's concrete layout/control values.
Neither the installer nor its access specifications choose these requirements. -/
def InputInstalled {Δ : Ctx} {q : Setoid (Env Δ)} {Value : Type}
    (p : Profile Δ q Value) (wanted ambient loaded : Env Δ) : Prop :=
  (∀ v ∈ p.inputViews, v.read loaded = v.read wanted) ∧
  (∀ b ∈ p.boundaryValues, b.destination.read loaded = b.value wanted ambient)

/-- Input views and boundary values together cover the intended target input
state. The caller fixes inputQ independently of the installer; harness-private
state need not be distinguished by it. This does not replace noninterference. -/
def InstallationCoverage
    {Δ : Ctx} {q : Setoid (Env Δ)} {Value : Type}
    (p : Profile Δ q Value) (inputQ : Setoid (Env Δ)) : Prop :=
  ∀ wanted ambient loaded,
    InputInstalled p wanted ambient loaded →
    inputQ.r loaded wanted

/-- Faithful AND complete recovery relative to the fixed quotient. The first
law permits no extra distinctions inside a class and loses none between classes.
The second supplies actual recovery of that class from the representation.
This is required independently of admission and before quantifying over runs:
fail-all execution cannot excuse an incomplete representation. -/
def ObservationComplete {Δ : Ctx} {q : Setoid (Env Δ)} {Value : Type}
    (p : Profile Δ q Value) : Prop :=
  (∀ s t, p.observe s = p.observe t ↔ q.r s t) ∧
  (∀ s, p.recover (p.observe s) = some (Quotient.mk q s))

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
def ComponentObligations {Δ : Ctx} {q : Setoid (Env Δ)} {m : Nat} {Value : Type}
    (inputQ : Setoid (Env Δ)) (p : Profile Δ q Value) (c : Construction Δ m Value) : Prop :=
  InstallationCoverage p inputQ ∧
  ObservationComplete p ∧
  (∀ wanted ambient,
    StageCorrect (compose c.basis c.install).denotes
      (fun s => s = c.prepare wanted ambient)
      (fun _ loaded => InputInstalled p wanted ambient loaded ∧
        p.installFrame wanted ambient loaded)) ∧
  StageCorrect (fun post final =>
      (compose c.basis c.capture).denotes (c.handoff post) final)
    (fun _ => True)
    (fun post final => c.decode (Env.lookup final c.memory) = p.observe post ∧
      p.recover (c.decode (Env.lookup final c.memory)) = some (Quotient.mk q post) ∧
      p.captureFrame post final)

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
paired unchanged with the decoded value in this semantic statement. Native
metadata acquisition/reporting is not proved by that reflexive event equality.
This is the completed-stage semantic obligation; it is deliberately not named
native e2e correctness. Native linkage, prefix recovery and actual execution
termination remain separate obligations in the existing observer specification. -/
def BootstrapObligation {Δ : Ctx} {q : Setoid (Env Δ)} {m : Nat} {Value : Type}
    (inputQ : Setoid (Env Δ)) (p : Profile Δ q Value) (c : Construction Δ m Value) : Prop :=
  InstallationCoverage p inputQ ∧
  ObservationComplete p ∧
  ∀ wanted ambient,
    (∃ loaded, (compose c.basis c.install).denotes
      (c.prepare wanted ambient) loaded) ∧
    (∀ (Event : Type) (T : Env Δ → Event → Env Δ → Prop)
      event loaded post final, Run c T wanted ambient event loaded post final →
      InputInstalled p wanted ambient loaded ∧ inputQ.r loaded wanted ∧ p.installFrame wanted ambient loaded ∧
      (event, c.decode (Env.lookup final c.memory)) = (event, p.observe post) ∧
      p.recover (c.decode (Env.lookup final c.memory)) = some (Quotient.mk q post) ∧
      p.captureFrame post final) ∧
    (∀ (Event : Type) (T : Env Δ → Event → Env Δ → Prop)
      event loaded post,
      (compose c.basis c.install).denotes (c.prepare wanted ambient) loaded →
      T loaded event post → ∃ final, Run c T wanted ambient event loaded post final)

/-- The reusable theorem obligation. A future proof can eliminate StageCorrect
in ComponentObligations without inspecting or executing T. AYXG composition
lemmas support proving those component obligations from the basis semantics. -/
def CompositionTheorem : Prop :=
  ∀ (Δ : Ctx) (q inputQ : Setoid (Env Δ)) (m : Nat) (Value : Type)
    (p : Profile Δ q Value) (c : Construction Δ m Value),
    ComponentObligations inputQ p c → BootstrapObligation inputQ p c

/-- Concrete frame meaning: every designated view retains its original value.
The protected views are fixed by the observer profile, not selected by an
implementation to excuse its effects. They can include memory outside a record. -/
def Preserves {Δ : Ctx} (preserved : List (StateView Δ))
    (before after : Env Δ) : Prop :=
  ∀ v ∈ preserved, v.read after = v.read before

/-- A required transfer into a state view. `value` reads the PRE-state; it may
express copying, conversion, indexing, or a coordinated stack-position update.
Its meaning is supplied by the specification, not inferred from a mnemonic. -/
structure ViewTransfer (Δ : Ctx) where
  destination : StateView Δ
  value : Env Δ → destination.Value

/-- Specification data only. An access may change several overlapping views.
No purity, independent-register, move, or stack discipline is assumed. Changes
not constrained here must still satisfy the subsequent sequence obligations. -/
structure AccessSpec (Δ : Ctx) where
  enabled : Env Δ → Prop
  transfers : List (ViewTransfer Δ)
  preserved : List (StateView Δ)

def AccessEffect {Δ : Ctx} (a : AccessSpec Δ) (before after : Env Δ) : Prop :=
  (∀ t ∈ a.transfers, t.destination.read after = t.value before) ∧
  Preserves a.preserved before after

/-- Obligation for an ARBITRARY quantified AYXG transition. Each instance must
prove enabled execution and the required transfers/preservation from its full
semantics. This does not replace those semantics with an effect summary. -/
def AccessCorrect {Δ : Ctx} (step : QFAbvStep Δ Δ) (a : AccessSpec Δ) : Prop :=
  StageCorrect step.denotes a.enabled (AccessEffect a)

/-- A compositional certificate obligation. Intermediate assertions can express
where original information has been saved or encoded. The implication covers
EVERY state pair permitted by the access specification, so omitted side effects
cannot be silently relied on as preserving information. No target is executed.
The empty sequence must already imply the required final assertion. -/
def AccessSequence {Δ : Ctx} {m : Nat} (basis : Basis Δ m)
    (spec : Fin m → AccessSpec Δ) :
    List (Fin m) → (Env Δ → Prop) → (Env Δ → Prop) → Prop
  | [], pre, post => ∀ s, pre s → post s
  | i :: rest, pre, post =>
      AccessCorrect (basis.model i) (spec i) ∧
      (∀ s, pre s → (spec i).enabled s) ∧
      ∃ next : Env Δ → Prop,
        (∀ before after, pre before → AccessEffect (spec i) before after → next after) ∧
        AccessSequence basis spec rest next post

/-- Generic composition theorem obligation, not a proof. It quantifies over
all bases and access specifications; architecture instances discharge premises. -/
def AccessComposition : Prop :=
  ∀ (Δ : Ctx) (m : Nat) (basis : Basis Δ m) (spec : Fin m → AccessSpec Δ)
    (steps : List (Fin m)) (pre post : Env Δ → Prop),
    AccessSequence basis spec steps pre post →
    StageCorrect (compose basis steps).denotes pre (fun _ final => post final)

/-- Installation contract over arbitrary AYXG access operations. The fixed
profile determines requested views, boundary values and preserved surroundings.
The sequence must establish all three, not just some predicate named entry.
This is completed-stage correctness, not native termination or prefix recovery. -/
def InstallerContract {Δ : Ctx} {q : Setoid (Env Δ)} {m : Nat} {Value : Type}
    (inputQ : Setoid (Env Δ)) (p : Profile Δ q Value) (c : Construction Δ m Value)
    (spec : Fin m → AccessSpec Δ) (installProtected : List (StateView Δ)) : Prop :=
  InstallationCoverage p inputQ ∧
  (∀ wanted ambient loaded,
    p.installFrame wanted ambient loaded ↔ Preserves installProtected ambient loaded) ∧
  (∀ wanted ambient,
    AccessSequence c.basis spec c.install
      (fun s => s = c.prepare wanted ambient)
      (fun loaded =>
        (∀ v ∈ p.inputViews, v.read loaded = v.read wanted) ∧
        (∀ b ∈ p.boundaryValues, b.destination.read loaded = b.value wanted ambient) ∧
        Preserves installProtected ambient loaded))

/-- Capture contract over arbitrary AYXG access operations. The final record
must recover the ORIGINAL target post-state modulo the fixed quotient, while
preserving the fixed surrounding views. Intermediate information may relocate.
No correctness premise about the observed target instruction is used. -/
def CapturerContract {Δ : Ctx} {q : Setoid (Env Δ)} {m : Nat} {Value : Type}
    (p : Profile Δ q Value) (c : Construction Δ m Value)
    (spec : Fin m → AccessSpec Δ) (captureProtected : List (StateView Δ)) : Prop :=
  ObservationComplete p ∧
  (∀ post final, p.captureFrame post final ↔ Preserves captureProtected post final) ∧
  (∀ post,
    AccessSequence c.basis spec c.capture (fun s => s = c.handoff post)
      (fun final => c.decode (Env.lookup final c.memory) = p.observe post ∧
        p.recover (c.decode (Env.lookup final c.memory)) = some (Quotient.mk q post) ∧
        Preserves captureProtected post final))

/-- Both named contracts concern the same fixed profile and construction. -/
def AccessFrameObligations {Δ : Ctx} {q : Setoid (Env Δ)} {m : Nat} {Value : Type}
    (inputQ : Setoid (Env Δ)) (p : Profile Δ q Value) (c : Construction Δ m Value)
    (spec : Fin m → AccessSpec Δ)
    (installProtected captureProtected : List (StateView Δ)) : Prop :=
  InstallerContract inputQ p c spec installProtected ∧ CapturerContract p c spec captureProtected

/-- Required connection to the existing observer bootstrap, without a premise
about the target instruction's semantics. Both composition results remain proof
obligations; defining these Props does not discharge them. -/
def AccessToBootstrap : Prop :=
  AccessComposition → CompositionTheorem →
  ∀ (Δ : Ctx) (q inputQ : Setoid (Env Δ)) (m : Nat) (Value : Type)
    (p : Profile Δ q Value) (c : Construction Δ m Value)
    (spec : Fin m → AccessSpec Δ) (installProtected captureProtected : List (StateView Δ)),
    AccessFrameObligations inputQ p c spec installProtected captureProtected → BootstrapObligation inputQ p c

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

/-- Requested memory is part of the installation requirement, not presumed
present in ambient memory. The fixed request selects its byte addresses; every
selected byte must equal wanted at target entry. SparseInstaller supplies the
sparse preparation extension and its installer certificate. Capture still has
its existing GPR-only decoder. -/
def movProfile (requestedMemory : List (BitVec 64)) (q : Setoid (Env Γ))
    (recover : List (BitVec 64) → Option (Quotient q)) :
    Profile Γ q (List (BitVec 64)) where
  inputViews :=
    [⟨List (BitVec 64), observeGprs⟩,
     ⟨({a : BitVec 64 // a ∈ requestedMemory} → BitVec 8),
       fun s a => Env.lookup s v_mem a.val⟩]
  boundaryValues :=
    [⟨⟨BitVec 64, fun s => Env.lookup s v_rip⟩,
       fun _ _ => BitVec.ofNat 64 0x400170⟩]
  observe := observeGprs
  recover := recover
  installFrame _ ambient loaded :=
    StateFrame inputChangedFields (requestedMemory ++ inputWrites.map Prod.fst) ambient loaded
  captureFrame post final :=
    StateFrame captureChangedFields (expectedWrites.map Prod.fst) post final

/-- Pin the concrete supervisor helpers to their intended roles; they cannot
stand in for the MOV load/capture by installing registers or copying the answer.
Their native refinement is still a separate obligation. -/
def MovPreparationFrame (requestedMemory : List (BitVec 64)) : Prop :=
  ∀ wanted ambient,
    StateFrame [⟨_, v_mem⟩, ⟨_, v_rip⟩] (requestedMemory ++ inputWrites.map Prod.fst)
      ambient (prepareInput wanted ambient)

def MovHandoffFrame : Prop :=
  ∀ post, StateFrame [⟨_, v_rip⟩] [] post (enterCapture post) ∧
    Env.lookup (enterCapture post) v_rip = BitVec.ofNat 64 0x400000

def MovComponentObligations (requestedMemory : List (BitVec 64)) (q inputQ : Setoid (Env Γ))
    (recover : List (BitVec 64) → Option (Quotient q)) : Prop :=
  ComponentObligations inputQ (movProfile requestedMemory q recover) movConstruction ∧ MovPreparationFrame requestedMemory ∧ MovHandoffFrame

def MovBootstrapObligation (requestedMemory : List (BitVec 64)) (q inputQ : Setoid (Env Γ))
    (recover : List (BitVec 64) → Option (Quotient q)) : Prop :=
  BootstrapObligation inputQ (movProfile requestedMemory q recover) movConstruction ∧ MovPreparationFrame requestedMemory ∧ MovHandoffFrame

end MovObserver.Bootstrap
