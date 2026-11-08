import Pipeline

set_option maxRecDepth 16384
set_option maxHeartbeats 2000000

namespace MovObserver
open Ayxg.QfAbv
open Ayxg.LTS.QfAbv (SymbolicTransitionSystem Config)
variable [FPInterpretation]

/-- The actual three modeled stages, with intermediate states explicit.
The target may have any labeled outcome. The supervisor saves that outcome
and PC before redirecting the stopped state to the capture fragment.

This is the modeled protocol, not a theorem that Linux ptrace implements it.
In particular, `enterCapture` is the specified OS handoff operation. -/
structure ProtocolExecution {C E : Type}
    (target : SymbolicTransitionSystem C Γ E)
    (control : C) (wanted ambient : Env Γ) (edge : E) (post : Config C Γ) where
  loaded : Env Γ
  captured : Env Γ
  inputStep : loadStep.denotes (prepareInput wanted ambient) loaded
  targetStep : target.toLTS.Tr ⟨control, loaded⟩ edge post
  captureStep : MovObserver.captureStep.denotes (enterCapture post.env) captured

def ProtocolExecution.observation {C E : Type}
    {target : SymbolicTransitionSystem C Γ E}
    {control : C} {wanted ambient : Env Γ} {edge : E} {post : Config C Γ}
    (run : ProtocolExecution target control wanted ambient edge post) : Observation C E :=
  ⟨post.control, edge, Env.lookup post.env v_rip,
    decodeRecord (Env.lookup run.captured v_mem)⟩

/-- Preparing the private input slots and executing the extracted loader cannot
change any other modeled memory byte before the original target step. -/
theorem protocol_input_memory_frame {C E : Type}
    {target : SymbolicTransitionSystem C Γ E}
    {control : C} {wanted ambient : Env Γ} {edge : E} {post : Config C Γ}
    (run : ProtocolExecution target control wanted ambient edge post)
    (a : BitVec 64)
    (outside : ∀ w ∈ inputWrites, a ≠ w.1) :
    Env.lookup run.loaded v_mem a = Env.lookup ambient v_mem a := by
  have input := run.inputStep.2
  change loadUpdate.eval (prepareInput wanted ambient) = run.loaded at input
  rw [← input, loader_preserves_mem]
  cases ambient with
  | cons memory tail =>
    cases tail with
    | cons pc rest =>
      exact writes_frame wanted inputWrites memory a outside

/-- The existing loader falls through to this exact target address; it does
not install an arbitrary requested RIP. -/
theorem protocol_loaded_pc {C E : Type}
    {target : SymbolicTransitionSystem C Γ E}
    {control : C} {wanted ambient : Env Γ} {edge : E} {post : Config C Γ}
    (run : ProtocolExecution target control wanted ambient edge post) :
    Env.lookup run.loaded v_rip = BitVec.ofNat 64 4194672 := by
  rw [← run.inputStep.2]
  rfl

/-- Completed-stage frame: field allowance plus a concrete byte footprint.
This does not claim the footprint is minimal or private; actual footprints
and their separation from target memory/code require independent review. -/
def StateFrame (changed : List (Σ s : TermSort, Var Γ s))
    (writes : List (BitVec 64)) (before after : Env Γ) : Prop :=
  (∀ (s : TermSort) (v : Var Γ s),
    (⟨s, v⟩ : Σ t : TermSort, Var Γ t) ∉ changed →
    Env.lookup after v = Env.lookup before v) ∧
  (∀ a : BitVec 64, a ∉ writes →
    Env.lookup after v_mem a = Env.lookup before v_mem a)

/-- Fields intentionally changed by input preparation and GPR loading.
Memory is framed separately at byte granularity; RIP is the fixed loader
fallthrough, and the sixteen GPRs receive the requested values. -/
def inputChangedFields : List (Σ s : TermSort, Var Γ s) :=
  [⟨_, v_mem⟩, ⟨_, v_rip⟩,
   ⟨_, v_rax⟩, ⟨_, v_rcx⟩, ⟨_, v_rdx⟩, ⟨_, v_rbx⟩,
   ⟨_, v_rsp⟩, ⟨_, v_rbp⟩, ⟨_, v_rsi⟩, ⟨_, v_rdi⟩,
   ⟨_, v_r8⟩, ⟨_, v_r9⟩, ⟨_, v_r10⟩, ⟨_, v_r11⟩,
   ⟨_, v_r12⟩, ⟨_, v_r13⟩, ⟨_, v_r14⟩, ⟨_, v_r15⟩]

/-- Unproved obligation for the existing preparation and loader, independent
of whether a subsequent target or capture succeeds. Every other field in Γ
must retain its ambient value; only input-slot bytes may change in memory.
This frames the current modeled state, not fields absent from Γ or native
mapping/permission behavior. GPR fidelity and fixed RIP are separate claims. -/
def ProtocolInputStateFrame : Prop :=
  ∀ (wanted ambient loaded : Env Γ),
    loadStep.denotes (prepareInput wanted ambient) loaded →
    StateFrame inputChangedFields (inputWrites.map Prod.fst) ambient loaded

/-- Only RIP and capture-record memory may differ after the modeled handoff
and completed capture. Memory is framed separately at byte granularity. -/
def captureChangedFields : List (Σ s : TermSort, Var Γ s) :=
  [⟨_, v_mem⟩, ⟨_, v_rip⟩]

/-- Unproved endpoint-frame obligation for the existing handoff and capture.
Compare with the original post-target state, before enterCapture redirects RIP.
Every other field in Γ and every byte outside the capture record must survive.
This does not assert intermediate-prefix or native fault behavior, nor that
fields absent from Γ are represented. Saved target PC/event and record decoding
are separate fidelity claims, not inferred from this frame. -/
def ProtocolCaptureHandoffFrame : Prop :=
  ∀ (post captured : Env Γ),
    captureStep.denotes (enterCapture post) captured →
    StateFrame captureChangedFields (expectedWrites.map Prod.fst) post captured

/-- Exact current model representation, without normalizing flag encodings.
The 64-bit d/ac/id fields are retained verbatim, not asserted to be raw RFLAGS
bits. This is not a claim that Γ represents every architectural flag. -/
structure ModeledFlags where
  cf : BitVec 1
  pf : BitVec 1
  af : BitVec 1
  zf : BitVec 1
  sf : BitVec 1
  of_ : BitVec 1
  d : BitVec 64
  ac : BitVec 64
  id : BitVec 64

def observeModeledFlags (s : Env Γ) : ModeledFlags :=
  ⟨Env.lookup s v_rflags_CF, Env.lookup s v_rflags_PF,
   Env.lookup s v_rflags_AF, Env.lookup s v_rflags_ZF,
   Env.lookup s v_rflags_SF, Env.lookup s v_rflags_OF,
   Env.lookup s v_d, Env.lookup s v_ac, Env.lookup s v_id⟩

/-- VEX AMD64 representation invariant, not an arbitrary coverage restriction.
Source: VEX fd41c675d50845b0aadd0b42ac7490038e2f3d82,
libvex_guest_amd64.h and LibVEX_GuestAMD64_get/put_rflags. -/
def ModeledFlags.Valid (f : ModeledFlags) : Prop :=
  (f.d = 1 ∨ f.d = BitVec.ofNat 64 (2^64 - 1)) ∧
  (f.ac = 0 ∨ f.ac = 1) ∧ (f.id = 0 ∨ f.id = 1)

instance (f : ModeledFlags) : Decidable f.Valid :=
  inferInstanceAs (Decidable ((f.d = 1 ∨ f.d = BitVec.ofNat 64 (2^64 - 1)) ∧
    (f.ac = 0 ∨ f.ac = 1) ∧ (f.id = 0 ∨ f.id = 1)))

/-- Decode only the nine represented flags; no claim of full RFLAGS coverage. -/
def flagsFromRflags (word : BitVec 64) : ModeledFlags :=
  let bit (n : Nat) : BitVec 1 := if word.getLsbD n then 1 else 0
  ⟨bit 0, bit 2, bit 4, bit 6, bit 7, bit 11,
   if word.getLsbD 10 then BitVec.ofNat 64 (2^64 - 1) else 1,
   if word.getLsbD 18 then 1 else 0,
   if word.getLsbD 21 then 1 else 0⟩

def modeledRflagsMask : BitVec 64 :=
  BitVec.ofNat 64 (2^0 + 2^2 + 2^4 + 2^6 + 2^7 + 2^10 + 2^11 + 2^18 + 2^21)

/-- Patch the represented flags into a supplied word, preserving every other
bit (including reserved bits). Reject invalid VEX encodings rather than
normalizing them. This does not assert that the OS permits writing the word. -/
def flagsToRflags (f : ModeledFlags) (original : BitVec 64) : Option (BitVec 64) :=
  if f.Valid then
    let bits := BitVec.ofNat 64
      (f.cf.toNat * 2^0 + f.pf.toNat * 2^2 + f.af.toNat * 2^4 +
       f.zf.toNat * 2^6 + f.sf.toNat * 2^7 + f.of_.toNat * 2^11 +
       (if f.d = BitVec.ofNat 64 (2^64 - 1) then 2^10 else 0) +
       f.ac.toNat * 2^18 + f.id.toNat * 2^21)
    some ((original &&& ~~~modeledRflagsMask) ||| bits)
  else none

/-- Unproved codec obligation for the concrete conversions above. Decoding
always yields canonical model flags. Encoding valid flags must succeed and
recover exactly those flags while framing every unmodeled bit. Decoding and
patching the original word back must recover that entire word. Invalid model
encodings are rejected exactly, not normalized. These are codec laws, not a
claim of full architectural coverage or permission to install a native word. -/
def FlagsConversionCorrect : Prop :=
  (∀ word : BitVec 64, (flagsFromRflags word).Valid) ∧
  (∀ (f : ModeledFlags) (original : BitVec 64), f.Valid →
    ∃ encoded : BitVec 64,
      flagsToRflags f original = some encoded ∧
      flagsFromRflags encoded = f ∧
      (encoded &&& ~~~modeledRflagsMask) =
        (original &&& ~~~modeledRflagsMask)) ∧
  (∀ word : BitVec 64,
    flagsToRflags (flagsFromRflags word) word = some word) ∧
  (∀ (f : ModeledFlags) (original : BitVec 64),
    flagsToRflags f original = none ↔ ¬ f.Valid)

/-- Independent bit-position specification for the nine represented AMD64
flags. Literal positions are grounded in the pinned VEX get/put_rflags source,
not derived from modeledRflagsMask or either conversion implementation.
Other RFLAGS bits are outside this relation, not asserted to be zero. -/
def FlagsMatchRflags (f : ModeledFlags) (word : BitVec 64) : Prop :=
  f.Valid ∧
  (word.getLsbD 0 = true ↔ f.cf = 1) ∧
  (word.getLsbD 2 = true ↔ f.pf = 1) ∧
  (word.getLsbD 4 = true ↔ f.af = 1) ∧
  (word.getLsbD 6 = true ↔ f.zf = 1) ∧
  (word.getLsbD 7 = true ↔ f.sf = 1) ∧
  (word.getLsbD 11 = true ↔ f.of_ = 1) ∧
  (word.getLsbD 10 = true ↔ f.d = BitVec.ofNat 64 (2^64 - 1)) ∧
  (word.getLsbD 18 = true ↔ f.ac = 1) ∧
  (word.getLsbD 21 = true ↔ f.id = 1)

/-- Unproved architectural-layout obligation, separate from codec roundtrips.
The decoder must match the fixed bit specification for every word; every
successful encoding must match the supplied flags. Encoding availability,
invalid rejection and unrelated-bit preservation remain FlagsConversionCorrect.
This is representation correspondence, not native write permission or complete
architectural-state coverage. -/
def FlagsArchitecturalLayoutCorrect : Prop :=
  (∀ word : BitVec 64, FlagsMatchRflags (flagsFromRflags word) word) ∧
  (∀ (f : ModeledFlags) (original encoded : BitVec 64),
    flagsToRflags f original = some encoded → FlagsMatchRflags f encoded)

/-- Classification evidence retains the exact observed model fields in both
cases. Invalid is a representation failure, not a successful comparison or
an absent sample. This record does not describe native instruction faults. -/
inductive FlagsBoundaryResult where
  | valid (flags : ModeledFlags)
  | invalidEncoding (flags : ModeledFlags)

/-- Unproved obligation for a boundary classifier over actual model state.
Every state is covered, including noncanonical d/ac/id values. The result
must retain those values verbatim, without normalization or model prediction.
The same contract applies to requested, ambient and post-target model states.
It does not establish that the executable calls the classifier or propagates
invalidEncoding: those sequencing/reporting obligations remain for the Lean
orchestrator, which must not discard invalid results or count them as passes. -/
def FlagsBoundaryClassificationCorrect
    (classify : Env Γ → FlagsBoundaryResult) : Prop :=
  ∀ state : Env Γ,
    classify state =
      if (observeModeledFlags state).Valid then
        FlagsBoundaryResult.valid (observeModeledFlags state)
      else
        FlagsBoundaryResult.invalidEncoding (observeModeledFlags state)

/-- Flag installation may change only represented flags, RIP and declared
memory bytes. Preparation has the same allowance so supervisor installation
is permitted; it is not forced through a ceremonial instruction fragment. -/
def flagsInstallChangedFields : List (Σ s : TermSort, Var Γ s) :=
  [⟨_, v_mem⟩, ⟨_, v_rip⟩,
   ⟨_, v_rflags_CF⟩, ⟨_, v_rflags_PF⟩, ⟨_, v_rflags_AF⟩,
   ⟨_, v_rflags_ZF⟩, ⟨_, v_rflags_SF⟩, ⟨_, v_rflags_OF⟩,
   ⟨_, v_d⟩, ⟨_, v_ac⟩, ⟨_, v_id⟩]

/-- Unproved binding of the flags decoder to an eight-byte little-endian
RFLAGS record at a fixed base. read64 is the existing concrete byte decoder;
flagsFromRflags is the existing architectural conversion. No requested values
or predicted post-state enter decoding. Every memory is covered, so reject-all
or alternate-record decoders cannot satisfy this obligation.
The base must permit eight contiguous addresses without 64-bit wraparound.
Memory here is total: readability, short native transfers, record acquisition,
and agreement of the capture writer with this base remain separate obligations.
This does not claim all RFLAGS bits appear in ModeledFlags. -/
def FlagsRecordDecoderCorrect (recordBase : Nat)
    (decodeFlags : Mem 64 8 → Option ModeledFlags) : Prop :=
  recordBase + 8 ≤ 2^64 ∧
  ∀ memory : Mem 64 8,
    decodeFlags memory = some (flagsFromRflags (read64 memory recordBase))

/-- Unproved layout/separation obligation. The complete eight-byte flags
record must be admitted by the capture footprint. Every stage footprint must
avoid protected addresses, including target memory and executable code as
specified by the eventual layout. Footprints may overlap one another; this
predicate imposes no unnecessary pairwise separation or alignment constraint.
The protected predicate is fixed per layout, not inferred from observed writes.
Establishing that it includes every address needing protection is a separate
layout/target-access obligation; choosing False does not establish privacy.
This describes address separation, not native mapping or permissions. -/
def FlagsMemorySeparation (recordBase : Nat)
    (prepareWrites installWrites captureWrites : List (BitVec 64))
    (protectedAddress : BitVec 64 → Prop) : Prop :=
  recordBase + 8 ≤ 2^64 ∧
  (∀ i : Nat, i < 8 →
    BitVec.ofNat 64 (recordBase + i) ∈ captureWrites) ∧
  (∀ a : BitVec 64,
    a ∈ prepareWrites ∨ a ∈ installWrites ∨ a ∈ captureWrites →
    ¬ protectedAddress a)

/-- Flags observation retaining the original target metadata. C and E are
model control/outcome types, not a claim that native execution exposes a model
edge identifier. Their native correspondence remains a separate obligation. -/
structure FlagsObservation (C E : Type) where
  control : C
  edge : E
  savedPC : BitVec 64
  flags : ModeledFlags

/-- Unproved observation-assembly obligation. The assembler receives only
saved metadata and captured memory, never requested or predicted flag values.
Successful decoding must produce exactly that metadata and those decoded flags;
decoder failure must remain None. This does not prove the supervisor saved the
right metadata before handoff, acquired the right memory, or reports the result.
Those executable snapshot/acquisition/reporting links remain obligations. -/
def FlagsObservationCorrect {C E : Type}
    (decodeFlags : Mem 64 8 → Option ModeledFlags)
    (assemble : C → E → BitVec 64 → Mem 64 8 → Option (FlagsObservation C E)) : Prop :=
  ∀ (control : C) (edge : E) (savedPC : BitVec 64) (memory : Mem 64 8),
    assemble control edge savedPC memory =
      (decodeFlags memory).map fun flags =>
        ⟨control, edge, savedPC, flags⟩

/-- Availability plus all-result correctness; NOT a divergence-freedom claim. -/
def StageCorrect {I O : Type} (run : I → O → Prop)
    (admissible : I → Prop) (postcond : I → O → Prop) : Prop :=
  ∀ i, admissible i → (∃ o, run i o) ∧ ∀ o, run i o → postcond i o

/-- Data only: no correctness fields or assumed laws. -/
structure FlagsComponents (C E : Type) where
  prepare : Env Γ → Env Γ → Env Γ
  load : QFAbvStep Γ Γ
  capture : QFAbvStep Γ Γ
  decode : Mem 64 8 → Option ModeledFlags
  assemble : C → E → BitVec 64 → Mem 64 8 → Option (FlagsObservation C E)
  classify : Env Γ → FlagsBoundaryResult
  recordBase : Nat
  prepareWrites : List (BitVec 64)
  installWrites : List (BitVec 64)
  captureWrites : List (BitVec 64)
  protectedAddress : BitVec 64 → Prop
  loaderEntry : BitVec 64
  targetEntry : BitVec 64
  captureEntry : BitVec 64
  captureExit : BitVec 64

def admittedInput (i : Env Γ × Env Γ) : Prop :=
  (observeModeledFlags i.1).Valid ∧ (observeModeledFlags i.2).Valid

def PrepareCorrect {C E : Type} (p : FlagsComponents C E) : Prop :=
  StageCorrect (fun i s => s = p.prepare i.1 i.2) admittedInput fun i s =>
    StateFrame flagsInstallChangedFields p.prepareWrites i.2 s ∧
    Env.lookup s v_rip = p.loaderEntry

def LoadCorrect {C E : Type} (p : FlagsComponents C E) : Prop :=
  StageCorrect (fun i s => p.load.denotes (p.prepare i.1 i.2) s)
    admittedInput fun i s =>
      observeModeledFlags s = observeModeledFlags i.1 ∧
      StateFrame flagsInstallChangedFields p.installWrites (p.prepare i.1 i.2) s ∧
      Env.lookup s v_rip = p.targetEntry

def CaptureCorrect {C E : Type} (p : FlagsComponents C E) : Prop :=
  StageCorrect (fun post s => p.capture.denotes (enterCapture post) s)
    (fun post => (observeModeledFlags post).Valid) fun post s =>
      p.decode (Env.lookup s v_mem) = some (observeModeledFlags post) ∧
      StateFrame captureChangedFields p.captureWrites post s ∧
      Env.lookup s v_rip = p.captureExit

/-- Shared-parameter flags contract. These remain obligations, not assumed laws. -/
def FlagsProtocolContract {C E : Type} (p : FlagsComponents C E) : Prop :=
  PrepareCorrect p ∧ LoadCorrect p ∧ CaptureCorrect p ∧
  (∀ post, Env.lookup (enterCapture post) v_rip = p.captureEntry) ∧
  FlagsObservationCorrect p.decode p.assemble ∧
  FlagsConversionCorrect ∧ FlagsArchitecturalLayoutCorrect ∧
  FlagsRecordDecoderCorrect p.recordBase p.decode ∧
  FlagsMemorySeparation p.recordBase p.prepareWrites p.installWrites
    p.captureWrites p.protectedAddress ∧
  FlagsBoundaryClassificationCorrect p.classify


omit [FPInterpretation] in
/-- The reusable frame algebra; it says nothing about intermediate faults. -/
theorem stateFrame_compose
    (fieldsA fieldsB : List (Σ s : TermSort, Var Γ s))
    (bytesA bytesB : List (BitVec 64)) (a b c : Env Γ)
    (first : StateFrame fieldsA bytesA a b)
    (second : StateFrame fieldsB bytesB b c) :
    StateFrame (fieldsA ++ fieldsB) (bytesA ++ bytesB) a c := by
  constructor
  · intro sort v outside
    have ha : (⟨sort, v⟩ : Σ t : TermSort, Var Γ t) ∉ fieldsA :=
      fun h => outside (List.mem_append.mpr (Or.inl h))
    have hb : (⟨sort, v⟩ : Σ t : TermSort, Var Γ t) ∉ fieldsB :=
      fun h => outside (List.mem_append.mpr (Or.inr h))
    exact (second.1 sort v hb).trans (first.1 sort v ha)
  · intro address outside
    have ha : address ∉ bytesA :=
      fun h => outside (List.mem_append.mpr (Or.inl h))
    have hb : address ∉ bytesB :=
      fun h => outside (List.mem_append.mpr (Or.inr h))
    exact (second.2 address hb).trans (first.2 address ha)


/-- Unproved composition obligation for the modeled flags protocol.
The component contract is a conjunct to discharge, not an assumed correctness
law for project-owned code. Preparation/loading must exist for valid inputs;
every loaded successor installs the requested flags and frames ambient state.
Every target edge from that exact loaded state is covered, without assuming
that the target agrees with native semantics or preserves flag validity.
Invalid target flags retain an explicit invalid classification. Valid outcomes
admit capture, and every capture successor must preserve the original target
metadata in the assembled observation and satisfy the post-target frame.

This uses the existing one-step target LTS, enterCapture, and concrete modeled
state. It does not prove native execution, actual metadata acquisition, call
sequencing/termination, or invalid-result reporting by the Lean executable.
GPR/FP/vector installation is not added by this flags-only composition: GPRs
are preserved from ambient by its frame. No target successor is required if
the target LTS has none; target progress is a separate obligation. -/
def FlagsModeledEndToEnd {C E : Type}
    (target : SymbolicTransitionSystem C Γ E)
    (p : FlagsComponents C E) : Prop :=
  FlagsProtocolContract p ∧
  ∀ (wanted ambient : Env Γ),
    (observeModeledFlags wanted).Valid →
    (observeModeledFlags ambient).Valid →
    (∃ loaded, p.load.denotes (p.prepare wanted ambient) loaded) ∧
    (∀ loaded, p.load.denotes (p.prepare wanted ambient) loaded →
      observeModeledFlags loaded = observeModeledFlags wanted ∧
      Env.lookup loaded v_rip = p.targetEntry ∧
      StateFrame flagsInstallChangedFields (p.prepareWrites ++ p.installWrites)
        ambient loaded ∧
      ∀ (control : C) (edge : E) (post : Config C Γ),
        target.toLTS.Tr ⟨control, loaded⟩ edge post →
        (p.classify post.env =
          if (observeModeledFlags post.env).Valid then
            FlagsBoundaryResult.valid (observeModeledFlags post.env)
          else
            FlagsBoundaryResult.invalidEncoding (observeModeledFlags post.env)) ∧
        ((observeModeledFlags post.env).Valid →
          (∃ captured, p.capture.denotes (enterCapture post.env) captured) ∧
          (∀ captured, p.capture.denotes (enterCapture post.env) captured →
            p.assemble post.control edge (Env.lookup post.env v_rip)
                (Env.lookup captured v_mem) =
              some ⟨post.control, edge, Env.lookup post.env v_rip,
                observeModeledFlags post.env⟩ ∧
            StateFrame captureChangedFields p.captureWrites post.env captured ∧
            Env.lookup captured v_rip = p.captureExit)))

/-- Input fidelity, the identical target transition, exact output decoding,
and both input/capture memory frames follow from the extracted stub semantics.
No hypothesis asserts the observer's desired result. -/
theorem protocol_sound {C E : Type}
    {target : SymbolicTransitionSystem C Γ E}
    {control : C} {wanted ambient : Env Γ} {edge : E} {post : Config C Γ}
    (run : ProtocolExecution target control wanted ambient edge post) :
    observeGprs run.loaded = observeGprs wanted ∧
    Env.lookup run.loaded v_rip = BitVec.ofNat 64 4194672 ∧
    (∀ a, (∀ w ∈ inputWrites, a ≠ w.1) →
      Env.lookup run.loaded v_mem a = Env.lookup ambient v_mem a) ∧
    target.toLTS.Tr ⟨control, run.loaded⟩ edge post ∧
    run.observation = expectedObservation edge post ∧
    CaptureSpec (enterCapture post.env) run.captured := by
  have input := run.inputStep.2
  have output := run.captureStep.2
  refine ⟨?_, protocol_loaded_pc run, protocol_input_memory_frame run, run.targetStep, ?_,
    modeled_step_captures run.captureStep⟩
  · rw [← input]
    exact input_installed wanted ambient
  · unfold ProtocolExecution.observation
    rw [← output]
    exact capture_observation_exact edge post

/-- Every target outcome admitted by the current model can be observed by
this modeled protocol. It is not silently restricted to a normal-return edge.
Native faults during the observer itself are outside this total-memory model. -/
theorem protocol_complete {C E : Type}
    (target : SymbolicTransitionSystem C Γ E)
    {control : C} {wanted ambient : Env Γ} {edge : E} {post : Config C Γ}
    (step : target.toLTS.Tr
      ⟨control, loadUpdate.eval (prepareInput wanted ambient)⟩ edge post) :
    Nonempty (ProtocolExecution target control wanted ambient edge post) := by
  exact ⟨{
    loaded := loadUpdate.eval (prepareInput wanted ambient)
    captured := captureUpdate.eval (enterCapture post.env)
    inputStep := input_enables_loader wanted ambient
    targetStep := step
    captureStep := handoff_enables_capture post.env
  }⟩

#print axioms protocol_input_memory_frame
#print axioms protocol_loaded_pc
#print axioms protocol_sound
#print axioms protocol_complete
end MovObserver
