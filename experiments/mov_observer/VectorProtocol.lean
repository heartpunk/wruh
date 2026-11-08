import Protocol

namespace MovObserver.VectorProtocol
open Ayxg.QfAbv
variable [FPInterpretation]

/-- The exact current Γ fields; this does not infer native CPU/OS support. -/
def zmmVar (i : Fin 32) : Var Γ (.bv 512) :=
  ([v_zmm0, v_zmm1, v_zmm2, v_zmm3, v_zmm4, v_zmm5, v_zmm6, v_zmm7, v_zmm8, v_zmm9, v_zmm10, v_zmm11, v_zmm12, v_zmm13, v_zmm14, v_zmm15, v_zmm16, v_zmm17, v_zmm18, v_zmm19, v_zmm20, v_zmm21, v_zmm22, v_zmm23, v_zmm24, v_zmm25, v_zmm26, v_zmm27, v_zmm28, v_zmm29, v_zmm30, v_zmm31] : List (Var Γ (.bv 512))).get ⟨i.val, by simpa using i.isLt⟩

def maskVar (i : Fin 8) : Var Γ (.bv 64) :=
  ([v_k0, v_k1, v_k2, v_k3, v_k4, v_k5, v_k6, v_k7] : List (Var Γ (.bv 64))).get ⟨i.val, by simpa using i.isLt⟩

structure VectorValue where
  zmm : Fin 32 → BitVec 512
  mask : Fin 8 → BitVec 64

def observeVectors (s : Env Γ) : VectorValue :=
  ⟨fun i => Env.lookup s (zmmVar i), fun i => Env.lookup s (maskVar i)⟩

/-- Aliases are views of canonical ZMM storage, not independent state cells. -/
def xmm (v : VectorValue) (i : Fin 32) : BitVec 128 :=
  BitVec.extractLsb 127 0 (v.zmm i)
def ymm (v : VectorValue) (i : Fin 32) : BitVec 256 :=
  BitVec.extractLsb 255 0 (v.zmm i)

/-- Proposed canonical observation record: 32 full 64-byte ZMM values followed
by eight 8-byte mask values, each little-endian. No upper bits are normalized. -/
def VectorRecordMatches (base : Nat) (m : Mem 64 8) (v : VectorValue) : Prop :=
  base + 2112 ≤ 2^64 ∧
  (∀ i : Fin 32, ∀ b : Fin 64,
    m (BitVec.ofNat 64 (base + i.val * 64 + b.val)) =
      BitVec.ofNat 8 ((v.zmm i).toNat / 2^(8*b.val))) ∧
  (∀ i : Fin 8, ∀ b : Fin 8,
    m (BitVec.ofNat 64 (base + 2048 + i.val * 8 + b.val)) =
      BitVec.ofNat 8 ((v.mask i).toNat / 2^(8*b.val)))

def VectorDecoderCorrect (base : Nat)
    (decode : Mem 64 8 → Option VectorValue) : Prop :=
  base + 2112 ≤ 2^64 ∧
  (∀ m, ∃ v, decode m = some v) ∧
  (∀ m v, decode m = some v ↔ VectorRecordMatches base m v)

def installChangedFields : List (Σ s : TermSort, Var Γ s) :=
  [⟨_, v_mem⟩, ⟨_, v_rip⟩] ++
  (List.ofFn fun i : Fin 32 => (⟨_, zmmVar i⟩ : Σ s, Var Γ s)) ++
  (List.ofFn fun i : Fin 8 => (⟨_, maskVar i⟩ : Σ s, Var Γ s))

structure Components where
  prepare : Env Γ → Env Γ → Env Γ
  load : QFAbvStep Γ Γ
  capture : QFAbvStep Γ Γ
  decode : Mem 64 8 → Option VectorValue
  recordBase : Nat
  prepareWrites : List (BitVec 64)
  installWrites : List (BitVec 64)
  captureWrites : List (BitVec 64)
  protectedAddress : BitVec 64 → Prop
  loaderEntry : BitVec 64
  targetEntry : BitVec 64
  captureEntry : BitVec 64
  captureExit : BitVec 64

def InstallationCorrect (p : Components) : Prop :=
  (∀ wanted ambient,
    StateFrame installChangedFields p.prepareWrites ambient (p.prepare wanted ambient) ∧
    Env.lookup (p.prepare wanted ambient) v_rip = p.loaderEntry) ∧
  StageCorrect (fun i s => p.load.denotes (p.prepare i.1 i.2) s)
    (fun _ : Env Γ × Env Γ => True) fun i s =>
      observeVectors s = observeVectors i.1 ∧
      StateFrame installChangedFields p.installWrites (p.prepare i.1 i.2) s ∧
      Env.lookup s v_rip = p.targetEntry

def CaptureCorrect (p : Components) : Prop :=
  (∀ post, Env.lookup (enterCapture post) v_rip = p.captureEntry) ∧
  StageCorrect (fun post s => p.capture.denotes (enterCapture post) s)
    (fun _ => True) fun post s =>
      p.decode (Env.lookup s v_mem) = some (observeVectors post) ∧
      StateFrame captureChangedFields p.captureWrites post s ∧
      Env.lookup s v_rip = p.captureExit

/-- Fixed-layout separation, matching the approved flags pattern. Adequacy of
protectedAddress must follow from the real target/code layout; choosing it empty
is not a way to establish native noninterference. -/
def MemorySeparation (p : Components) : Prop :=
  p.recordBase + 2112 ≤ 2^64 ∧
  (∀ i : Nat, i < 2112 →
    BitVec.ofNat 64 (p.recordBase + i) ∈ p.captureWrites) ∧
  (∀ a : BitVec 64,
    a ∈ p.prepareWrites ∨ a ∈ p.installWrites ∨ a ∈ p.captureWrites →
    ¬ p.protectedAddress a)

/-- Full existing modeled vector domain, not a profile chosen after seeing
which tests pass. All bit patterns must install/capture; aliases retain exact
low bits. Completed endpoints must preserve GPRs, flags and FP fields. Prefix
faults, native feature exposure and concrete instruction effects remain separate
obligations: StateFrame alone does not permit erasing upper lanes mid-capture. -/
def VectorContract (p : Components) : Prop :=
  InstallationCorrect p ∧ CaptureCorrect p ∧
  VectorDecoderCorrect p.recordBase p.decode ∧ MemorySeparation p

end MovObserver.VectorProtocol
