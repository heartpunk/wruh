import MovInstaller
import WholeObserver

namespace MovObserver.Bootstrap
open Ayxg.QfAbv
open WholeObserver (SparseMemoryImage)
variable [FPInterpretation]

/-- Write every requested address. Repeated addresses are harmless because
all writes to an address use the same requested value. No ambient-value test. -/
def writeRequested (addresses : List (BitVec 64)) (wanted : Mem 64 8) :
    Mem 64 8 → Mem 64 8
  | ambient => addresses.foldl (fun memory a => Eval.memStore memory a (wanted a)) ambient

omit [FPInterpretation] in
theorem writeRequested_at (addresses : List (BitVec 64)) (wanted ambient : Mem 64 8)
    (a : BitVec 64) :
    writeRequested addresses wanted ambient a =
      if a ∈ addresses then wanted a else ambient a := by
  induction addresses generalizing ambient with
  | nil => simp [writeRequested]
  | cons b rest ih =>
    change writeRequested rest wanted (Eval.memStore ambient b (wanted b)) a = _
    rw [ih]
    by_cases h : a ∈ rest
    · simp [h]
    · by_cases eq : a = b
      · subst b; simp [h, Eval.memStore]
      · simp [h, eq, Eval.memStore]

/-- Replace only memory; all register state is retained. -/
def withMemory (memory : Mem 64 8) : Env Γ → Env Γ
  | .cons _ rest => .cons memory rest

/-- Sparse target bytes first, then the existing GPR input-slot preparation. -/
def prepareSparse (addresses : List (BitVec 64)) (wanted ambient : Env Γ) : Env Γ :=
  prepareInput wanted (withMemory
    (writeRequested addresses (Env.lookup wanted v_mem) (Env.lookup ambient v_mem)) ambient)

def sparseConstruction (addresses : List (BitVec 64)) : Construction Γ 2 (List (BitVec 64)) :=
  { movConstruction with prepare := prepareSparse addresses }

def requestedMemoryView (addresses : List (BitVec 64)) : StateView Γ where
  Value := {a : BitVec 64 // a ∈ addresses} → BitVec 8
  read s := fun a => Env.lookup s v_mem a.val

/-- Fixed installed input: all GPRs and every requested byte. The exact
loader's fallthrough PC remains a separately enforced boundary value. -/
def sparseInputQuotient (addresses : List (BitVec 64)) : Setoid (Env Γ) where
  r s t := observeGprs s = observeGprs t ∧
    (requestedMemoryView addresses).read s = (requestedMemoryView addresses).read t
  iseqv := ⟨fun _ => ⟨rfl, rfl⟩,
    fun h => ⟨h.1.symm, h.2.symm⟩,
    fun h k => ⟨h.1.trans k.1, h.2.trans k.2⟩⟩

def sparseOutsideMemory (addresses : List (BitVec 64)) : StateView Γ where
  Value := {a : BitVec 64 // a ∉ addresses ++ movInputSlots} → BitVec 8
  read s := fun a => Env.lookup s v_mem a.val

def sparseProtected (addresses : List (BitVec 64)) : List (StateView Γ) :=
  [movOtherFields, sparseOutsideMemory addresses]

/-- Only the existing loader's reserved input slots are excluded. This is a
layout condition, never a requirement that requested bytes already be present. -/
def SparseLayoutCompatible (addresses : List (BitVec 64)) : Prop :=
  ∀ a ∈ addresses, a ∉ movInputSlots

private theorem sparse_memory (addresses : List (BitVec 64)) (wanted ambient : Env Γ) :
    Env.lookup (prepareSparse addresses wanted ambient) v_mem =
      prepareInputMemory wanted
        (writeRequested addresses (Env.lookup wanted v_mem) (Env.lookup ambient v_mem)) := by
  cases ambient with | cons memory tail => cases tail; rfl

private theorem sparse_other (addresses : List (BitVec 64)) (wanted ambient : Env Γ) :
    movOtherFields.read (prepareSparse addresses wanted ambient) = movOtherFields.read ambient := by
  funext t v h
  cases v with
  | here => exact False.elim (h (by simp [inputChangedFields, v_mem]))
  | there v =>
    cases v with
    | here => exact False.elim (h (by simp [inputChangedFields, v_mem, v_rip]))
    | there v => cases ambient with | cons memory tail => cases tail; rfl

private theorem sparse_requested (addresses : List (BitVec 64))
    (layout : SparseLayoutCompatible addresses) (wanted ambient : Env Γ)
    (a : BitVec 64) (ha : a ∈ addresses) :
    Env.lookup (prepareSparse addresses wanted ambient) v_mem a = Env.lookup wanted v_mem a := by
  rw [sparse_memory]
  unfold prepareInputMemory
  rw [writes_frame]
  · simp [writeRequested_at, ha]
  · intro w hw eq
    exact layout a ha (eq ▸ List.mem_map.mpr ⟨w, hw, rfl⟩)

private theorem sparse_outside (addresses : List (BitVec 64)) (wanted ambient : Env Γ) :
    (sparseOutsideMemory addresses).read (prepareSparse addresses wanted ambient) =
      (sparseOutsideMemory addresses).read ambient := by
  funext a
  change Env.lookup (prepareSparse addresses wanted ambient) v_mem a.val = _
  rw [sparse_memory]
  unfold prepareInputMemory
  rw [writes_frame]
  · have outside : a.val ∉ addresses := fun h => a.property (List.mem_append_left _ h)
    simp only [writeRequested_at, outside, ite_false]
    rfl
  · intro w hw eq
    exact a.property (List.mem_append_right _ (eq ▸ List.mem_map.mpr ⟨w, hw, rfl⟩))

omit [FPInterpretation] in
private theorem sparse_frame (addresses : List (BitVec 64)) (before after : Env Γ) :
    StateFrame inputChangedFields (addresses ++ movInputSlots) before after ↔
      Preserves (sparseProtected addresses) before after := by
  constructor
  · intro h v hv
    simp only [sparseProtected, List.mem_cons, List.not_mem_nil, or_false] at hv
    rcases hv with rfl | rfl
    · funext t v outside; exact h.1 t v outside
    · funext a; exact h.2 a.val a.property
  · intro h
    constructor
    · intro t v outside
      exact congrFun (congrFun (congrFun
        (h movOtherFields (by simp [sparseProtected])) t) v) outside
    · intro a outside
      exact congrFun (h (sparseOutsideMemory addresses) (by simp [sparseProtected])) ⟨a, outside⟩

/-- Full installer certificate: every wanted state and every ambient state;
no assumption about ambient contents. Capture/recovery are not asserted here. -/
theorem sparse_installer_contract (addresses : List (BitVec 64))
    (layout : SparseLayoutCompatible addresses) (q : Setoid (Env Γ))
    (recover : List (BitVec 64) → Option (Quotient q)) :
    InstallerContract (sparseInputQuotient addresses) (movProfile addresses q recover)
      (sparseConstruction addresses) movInstallerAccess (sparseProtected addresses) := by
  refine ⟨?_, ?_, ?_⟩
  · intro wanted ambient loaded installed
    exact ⟨installed.1 ⟨List (BitVec 64), observeGprs⟩ (by simp [movProfile]),
      installed.1 (requestedMemoryView addresses) (by simp [movProfile, requestedMemoryView])⟩
  · intro wanted ambient loaded
    exact sparse_frame addresses ambient loaded
  · intro wanted ambient
    refine ⟨mov_loader_access_correct, ?_, ?_⟩
    · intro s hs
      subst s
      exact (input_enables_loader wanted (withMemory
        (writeRequested addresses (Env.lookup wanted v_mem) (Env.lookup ambient v_mem)) ambient)).1
    · refine ⟨fun after => AccessEffect movLoaderAccess (prepareSparse addresses wanted ambient) after, ?_, ?_⟩
      · intro before after hb effect
        subst before
        exact effect
      · intro loaded effect
        refine ⟨?_, ?_, ?_⟩
        · intro v hv
          simp only [movProfile, List.mem_cons, List.not_mem_nil, or_false] at hv
          rcases hv with rfl | rfl
          · have h := effect.1 ⟨⟨List (BitVec 64), observeGprs⟩, fun s => decodeInput (Env.lookup s v_mem)⟩ (by simp [movLoaderAccess])
            change observeGprs loaded = _ at h
            change observeGprs loaded = observeGprs wanted
            rw [h]
            exact (load_input _).symm.trans (input_installed wanted _)
          · funext a
            have h := effect.2 ⟨Mem 64 8, fun s => Env.lookup s v_mem⟩
              (by simp [movLoaderAccess])
            change Env.lookup loaded v_mem a.val = _
            change Env.lookup loaded v_mem = Env.lookup (prepareSparse addresses wanted ambient) v_mem at h
            rw [h]
            exact sparse_requested addresses layout wanted ambient a.val a.property
        · intro b hb
          simp only [movProfile, List.mem_cons, List.not_mem_nil, or_false] at hb
          rcases hb with rfl
          exact effect.1 ⟨⟨BitVec 64, fun s => Env.lookup s v_rip⟩, fun _ => BitVec.ofNat 64 0x400170⟩ (by simp [movLoaderAccess])
        · intro v hv
          simp only [sparseProtected, List.mem_cons, List.not_mem_nil, or_false] at hv
          rcases hv with rfl | rfl
          · exact (effect.2 _ (by simp [movLoaderAccess])).trans
              (sparse_other addresses wanted ambient)
          · have h := effect.2 ⟨Mem 64 8, fun s => Env.lookup s v_mem⟩
              (by simp [movLoaderAccess])
            exact (congrArg (fun m => fun a : {a : BitVec 64 // a ∉ addresses ++ movInputSlots} => m a.val) h).trans
              (sparse_outside addresses wanted ambient)

omit [FPInterpretation] in
/-- Nonoverlap and in-bounds range indexing make repeated byte addresses
consistent. This is proved from the image, not supplied as an extra premise. -/
theorem image_bytes_consistent (image : SparseMemoryImage)
    (a b : BitVec 64 × BitVec 8)
    (ha : a ∈ image.byteWrites) (hb : b ∈ image.byteWrites)
    (same : a.1 = b.1) : a.2 = b.2 := by
  obtain ⟨ra, hra, ha⟩ := List.mem_flatMap.mp ha
  obtain ⟨va, hva, ea⟩ := List.mem_map.mp ha
  obtain ⟨rb, hrb, hb⟩ := List.mem_flatMap.mp hb
  obtain ⟨vb, hvb, eb⟩ := List.mem_map.mp hb
  have ia := List.mem_zipIdx' hva
  have ib := List.mem_zipIdx' hvb
  have ba : ra.start + va.2 < 2^64 := by
    have := ra.ordered; have := ra.bounded; have := ra.size_eq
    have : va.2 < ra.bytes.size := by simpa using ia.1
    omega
  have bb : rb.start + vb.2 < 2^64 := by
    have := rb.ordered; have := rb.bounded; have := rb.size_eq
    have : vb.2 < rb.bytes.size := by simpa using ib.1
    omega
  have natSame : ra.start + va.2 = rb.start + vb.2 := by
    have h := congrArg BitVec.toNat ((congrArg Prod.fst ea).trans (same.trans (congrArg Prod.fst eb).symm))
    change (ra.start + va.2) % 2^64 = (rb.start + vb.2) % 2^64 at h
    rwa [Nat.mod_eq_of_lt ba, Nat.mod_eq_of_lt bb] at h
  have rel : ra = rb ∨ ra.endExclusive ≤ rb.start ∨ rb.endExclusive ≤ ra.start :=
    List.Pairwise.forall_of_forall_of_flip
      (R := fun a b : WholeObserver.MemoryRange => a = b ∨ a.endExclusive ≤ b.start ∨ b.endExclusive ≤ a.start)
      (fun _ _ => Or.inl rfl)
      (image.nonoverlapping.imp (fun h => Or.inr h))
      (image.nonoverlapping.imp (fun h => Or.inr (Or.symm h))) hra hrb
  rcases rel with eq | disjoint
  · subst rb
    have idx : va.2 = vb.2 := by omega
    have val : va.1 = vb.1 := by
      rw [ia.2, ib.2]; simp [idx]
    have := congrArg Prod.snd ea
    have := congrArg Prod.snd eb
    simpa using (congrArg Prod.snd ea).symm.trans (val.trans (congrArg Prod.snd eb))
  · have := ra.ordered; have := ra.size_eq
    have := rb.ordered; have := rb.size_eq
    have : va.2 < ra.bytes.size := by simpa using ia.1
    have : vb.2 < rb.bytes.size := by simpa using ib.1
    omega

/-- Executable stores of the concrete supplied payload. -/
def writePayload (writes : List (BitVec 64 × BitVec 8)) (ambient : Mem 64 8) : Mem 64 8 :=
  writes.foldl (fun memory w => Eval.memStore memory w.1 w.2) ambient

omit [FPInterpretation] in
private theorem payload_preserves (writes : List (BitVec 64 × BitVec 8))
    (a : BitVec 64) (v : BitVec 8)
    (consistent : ∀ w ∈ writes, w.1 = a → w.2 = v)
    (ambient : Mem 64 8) (initial : ambient a = v) :
    writePayload writes ambient a = v := by
  induction writes generalizing ambient with
  | nil => exact initial
  | cons w ws ih =>
    apply ih (fun b hb => consistent b (List.mem_cons_of_mem _ hb))
    change (if a = w.1 then w.2 else ambient a) = v
    split
    · rename_i eq; exact consistent w (by simp) eq.symm
    · exact initial

omit [FPInterpretation] in
private theorem payload_at (writes : List (BitVec 64 × BitVec 8))
    (consistent : ∀ a ∈ writes, ∀ b ∈ writes, a.1 = b.1 → a.2 = b.2)
    (w : BitVec 64 × BitVec 8) (hw : w ∈ writes) (ambient : Mem 64 8) :
    writePayload writes ambient w.1 = w.2 := by
  induction writes generalizing ambient with
  | nil => simp at hw
  | cons head tail ih =>
    change writePayload tail (Eval.memStore ambient head.1 head.2) w.1 = _
    rcases List.mem_cons.mp hw with eq | ht
    · subst head
      exact payload_preserves tail w.1 w.2
        (fun b hb eq => consistent b (by simp [hb]) w (by simp) eq)
        _ (by simp [Eval.memStore])
    · exact ih (fun a ha b hb => consistent a (by simp [ha]) b (by simp [hb])) ht _

def wantedForImage (image : SparseMemoryImage) (registers : Env Γ) : Env Γ :=
  withMemory (writePayload image.byteWrites (Env.lookup registers v_mem)) registers

/-- The concrete image entry point reuses exactly the certified preparation and
extracted loader. This evaluates the Lean state transformer, not a native FFI. -/
def installImage (image : SparseMemoryImage) (registers ambient : Env Γ) : Env Γ :=
  loadUpdate.eval (prepareSparse image.addresses (wantedForImage image registers) ambient)

theorem installImage_payload (image : SparseMemoryImage)
    (layout : SparseLayoutCompatible image.addresses) (registers ambient : Env Γ)
    (w : BitVec 64 × BitVec 8) (hw : w ∈ image.byteWrites) :
    Env.lookup (installImage image registers ambient) v_mem w.1 = w.2 := by
  unfold installImage
  rw [loader_preserves_mem, sparse_requested image.addresses layout]
  · have mem : Env.lookup (wantedForImage image registers) v_mem =
        writePayload image.byteWrites (Env.lookup registers v_mem) := by
      cases registers; rfl
    rw [mem]
    exact payload_at image.byteWrites (fun a ha b hb => image_bytes_consistent image a b ha hb) w hw _
  · exact List.mem_map.mpr ⟨w, hw, rfl⟩

/-- Preparation changes only memory and PC, not the registers whose loading
is delegated to the proved MOV fragment. -/
theorem prepareSparse_frame (addresses : List (BitVec 64)) (wanted ambient : Env Γ) :
    StateFrame [⟨_, v_mem⟩, ⟨_, v_rip⟩] (addresses ++ movInputSlots)
      ambient (prepareSparse addresses wanted ambient) := by
  constructor
  · intro t v outside
    cases v with
    | here => exact False.elim (outside (by simp [v_mem]))
    | there v =>
      cases v with
      | here => exact False.elim (outside (by simp [v_rip]))
      | there v => cases ambient with | cons memory tail => cases tail; rfl
  · intro a outside
    exact congrFun (sparse_outside addresses wanted ambient) ⟨a, outside⟩

theorem installImage_gprs (image : SparseMemoryImage) (registers ambient : Env Γ) :
    observeGprs (installImage image registers ambient) = observeGprs registers := by
  unfold installImage prepareSparse
  rw [input_installed]
  cases registers; rfl

theorem installImage_pc (image : SparseMemoryImage) (registers ambient : Env Γ) :
    Env.lookup (installImage image registers ambient) v_rip = BitVec.ofNat 64 0x400170 := by
  rfl

theorem installImage_frame (image : SparseMemoryImage) (registers ambient : Env Γ) :
    StateFrame inputChangedFields (image.addresses ++ movInputSlots)
      ambient (installImage image registers ambient) := by
  apply (sparse_frame image.addresses ambient _).mpr
  have run := input_enables_loader (wantedForImage image registers)
    (withMemory (writeRequested image.addresses
      (Env.lookup (wantedForImage image registers) v_mem) (Env.lookup ambient v_mem)) ambient)
  have effect := (mov_loader_access_correct _ run.1).2 _ run
  change AccessEffect movLoaderAccess
    (prepareSparse image.addresses (wantedForImage image registers) ambient)
    (installImage image registers ambient) at effect
  intro v hv
  simp only [sparseProtected, List.mem_cons, List.not_mem_nil, or_false] at hv
  rcases hv with rfl | rfl
  · exact (effect.2 movOtherFields (by simp [movLoaderAccess])).trans (sparse_other _ _ _)
  · have h := effect.2 ⟨Mem 64 8, fun s => Env.lookup s v_mem⟩ (by simp [movLoaderAccess])
    exact (congrArg (fun m => fun a : {a : BitVec 64 // a ∉ image.addresses ++ movInputSlots} => m a.val) h).trans
      (sparse_outside _ _ _)

#print axioms sparse_installer_contract
#print axioms installImage_payload
#print axioms prepareSparse_frame
#print axioms installImage_gprs
#print axioms installImage_frame
end MovObserver.Bootstrap
