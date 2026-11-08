import Wire

namespace MovObserver.RuntimeOwnership
open Bridge

/-- Same allocation incarnation as Bridge.Buffer, not a second heap address. -/
structure ObjectId where
  owner : Nat
  generation : Nat
  deriving DecidableEq

inductive Reference where
  | immediate (value : Nat)
  | heap (object : ObjectId)
  deriving DecidableEq

inductive Holder where
  | caller
  | bridge
  deriving DecidableEq

structure Right where
  holder : Holder
  reference : Reference
  deriving DecidableEq

/-- Logical ownership/accessor view projected from the SAME runtime state.
Roots denote distinct owned reference rights, not physical reference counts.
Children and tags must be bound to the pinned runtime's actual object accessors;
these projections are not an additional trusted runtime implementation. -/
structure View where
  host : HostState
  roots : Nat → Option Right
  children : ObjectId → List Reference
  tag : ObjectId → Option Nat

def Live (view : View) : Reference → Prop
  | .immediate value => value < 2^63
  | .heap object =>
      ∃ allocation, view.host.allocations object.owner = some allocation ∧
        allocation.owner = object.owner ∧ allocation.generation = object.generation ∧
        ¬ view.host.retired object.owner object.generation ∧ BufferValid allocation

def ViewValid (view : View) : Prop :=
  AllocationsSeparated view.host ∧
  (∀ root right, view.roots root = some right → Live view right.reference) ∧
  (∀ object, Live view (.heap object) →
    ∀ child ∈ view.children object, Live view child)

inductive Authority where
  | owned (root : Nat)
  | child (root : Nat) (index : Nat)

/-- A child accessor borrows through a live owned parent. Reading through it
is not acquisition of an independent ownership right. -/
def Authorized (view : View) (reference : Reference) : Authority → Prop
  | .owned root => ∃ right, view.roots root = some right ∧ Accessible actor borrowed root right ∧ right.reference = reference ∧
      Live view reference
  | .child root index => ∃ holder parent,
      view.roots root = some ⟨holder, .heap parent⟩ ∧
      Accessible actor borrowed root ⟨holder, .heap parent⟩ ∧ Live view (.heap parent) ∧
      (view.children parent)[index]? = some reference ∧ Live view reference

inductive Action where
  | retain (source : Authority) (root : Nat) (holder : Holder) (reference : Reference)
  | transfer (root : Nat) (fromHolder toHolder : Holder)
  | release (root : Nat) (holder : Holder)
  | allocate (root : Nat) (holder : Holder) (object : ObjectId)
  | immediate (root : Nat) (holder : Holder) (value : Nat)

def OtherRootsUnchanged (root : Nat) (before after : View) : Prop :=
  ∀ other, other ≠ root → after.roots other = before.roots other

/-- One exposed ownership action per step; absence means no ownership change.
Concrete binding must expose every action, including retain/release on failures.
Runtime allocation/initialization is separately bound to actual allocation events.
No physical refcount or mandatory deallocation is presumed (persistent values exist). -/
def ActionCorrect (before after : View) : Option Action → Prop
  | none => after.roots = before.roots
  | some (.retain source root holder reference) =>
      holder = actor ∧ Authorized before actor borrowed reference source ∧ before.roots root = none ∧
      after.roots root = some ⟨holder, reference⟩ ∧ OtherRootsUnchanged root before after
  | some (.transfer root fromHolder toHolder) =>
      fromHolder = actor ∧ ∃ reference, before.roots root = some ⟨fromHolder, reference⟩ ∧
        after.roots root = some ⟨toHolder, reference⟩ ∧ OtherRootsUnchanged root before after
  | some (.release root holder) =>
      holder = actor ∧ (∃ reference, before.roots root = some ⟨holder, reference⟩) ∧
      after.roots root = none ∧ OtherRootsUnchanged root before after
  | some (.allocate root holder object) =>
      holder = actor ∧ before.roots root = none ∧ ¬ Live before (.heap object) ∧ Live after (.heap object) ∧
      after.roots root = some ⟨holder, .heap object⟩ ∧ OtherRootsUnchanged root before after
  | some (.immediate root holder value) =>
      holder = actor ∧ before.roots root = none ∧ after.roots root = some ⟨holder, .immediate value⟩ ∧
      OtherRootsUnchanged root before after

/-- Raw foreign return precedes caller decoding. The retained boundary data
remains as ghost evidence even after the caller releases the physical wrapper. -/
inductive Phase where
  | foreign
  | returned (root : Nat) (raw : Except IO.Error ByteArray)

def actor : Phase → Holder
  | .foreign => .bridge
  | .returned _ _ => .caller

/-- Same initial state and writes, with steps ending at the raw return boundary.
Used only for interval-local lifetime/frame obligations, not as a fabricated
standalone decoded execution or a new termination assumption. -/
def ForeignSegment {State : Type} (e : Execution State) (phase : State → Phase) : Execution State :=
  { e with step := fun before after => e.step before after ∧ phase before = .foreign }

/-- Complete reference uses and ownership actions are fixed projections from
this execution, just like its existing complete write list. No omitted use or
fabricated retain may discharge the eventual concrete execution theorem. -/
def OwnershipSafety {State : Type} (e : Execution State) (view : State → View)
    (actions : State → State → Option Action) (phase : State → Phase) (borrowed : List Nat)
    (uses : State → State → List (Reference × Authority)) (request : Operation) : Prop :=
  ∀ state, Reaches e.step (e.initial request) state →
    ViewValid (view state) ∧
    ∀ next, e.step state next →
      ActionCorrect (actor (phase state)) borrowed (view state) (view next) (actions state next) ∧
      AllocationTransitionCorrect (view state).host (view next).host ∧
      (∀ use ∈ uses state next, Authorized (view state) (actor (phase state)) borrowed use.1 use.2)

/-- The borrowed request keeps its caller-owned reference and initialized wire
payload through the raw return boundary of the supplied foreign segment. BufferBytes describes size bytes, never array capacity.
Actual array/header layout must justify this exact payload slice. -/
def RequestBorrowPreserved {State : Type} (e : Execution State) (view : State → View)
    (request : Operation) (root : Nat) (payload : Buffer) (wire : ByteArray) : Prop :=
  Wire.FrameMatches (Wire.RequestFrame request) wire ∧
  ∀ state, Reaches e.step (e.initial request) state →
    (view state).roots root = some ⟨.caller, .heap ⟨payload.owner, payload.generation⟩⟩ ∧
    BorrowedFrom payload (view state).host ∧
    BufferBytes payload (view state).host.memory (wire.data.toList.map (fun b => b.toBitVec))

/-- Runtime IO results have tag 0/1 and one child. This states ownership/shape,
not the child's byte/error decoding. Wire.ForeignReturnMatches supplies the
value obligation once the actual child acquisition is bound to the same return. -/
def ResultRootOwned (view : View) (root : Nat) (raw : Except IO.Error ByteArray) : Prop :=
  ∃ wrapper child,
    view.roots root = some ⟨.caller, .heap wrapper⟩ ∧ Live view (.heap wrapper) ∧
    view.tag wrapper = some (match raw with | .ok _ => 0 | .error _ => 1) ∧
    view.children wrapper = [child] ∧ Live view child

/-- Complete phase discipline: a raw return must transfer a bridge-owned
wrapper right to the caller. Every final decoded result follows that boundary
and matches its original raw outcome. Missing raw-return records cannot satisfy
this contract together with termination. Caller extraction cannot reenter the
foreign call. Contents/accessor provenance still needs concrete runtime binding. -/
def ForeignReturnOwnership {State : Type} (e : Execution State) (view : State → View)
    (actions : State → State → Option Action) (phase : State → Phase)
    (request : Operation) : Prop :=
  phase (e.initial request) = .foreign ∧
  ∀ state, Reaches e.step (e.initial request) state →
    (∀ result, e.returned state = some result →
      ∃ root raw, phase state = .returned root raw ∧ Wire.ForeignReturnMatches raw result) ∧
    (∀ next, e.step state next →
      match phase state, phase next with
      | .foreign, .foreign => True
      | .foreign, .returned root raw =>
          actions state next = some (.transfer root .bridge .caller) ∧
          ResultRootOwned (view next) root raw
      | .returned _ _, .foreign => False
      | .returned root raw, .returned nextRoot nextRaw =>
          nextRoot = root ∧ nextRaw = raw)

/-- Shared-execution contract: ownership, wire borrowing and frames refer to
one host projection, and every returned outcome terminates. Apply under the
explicit external progress/resource premises, not an assumption that our own
code is correct. Concrete event/accessor completeness and raw-value acquisition
remain required binding obligations, not consequences of this conjunction. -/
def OwnedCallContract {State : Type} (e : Execution State) (view : State → View)
    (actions : State → State → Option Action)
    (uses : State → State → List (Reference × Authority))
    (phase : State → Phase)
    (request : Operation) (root : Nat) (payload : Buffer) (wire : ByteArray)
    (outputs scratch : State → List Buffer) : Prop :=
  OwnershipSafety e view actions phase [root] uses request ∧
  RequestBorrowPreserved (ForeignSegment e phase) view request root payload wire ∧
  ForeignReturnOwnership e view actions phase request ∧
  CallBufferLifetime (ForeignSegment e phase) (fun state => (view state).host) request [payload] ∧
  CallDynamicMemoryFrame (ForeignSegment e phase) (fun state => (view state).host) request [payload] outputs scratch ∧
  CallTerminates e request ∧ CallReplyCompatible e

end MovObserver.RuntimeOwnership
