# Smaller observer contracts: ten-minute design result

Scope: simplify the specifications for a faithful, noninterfering native
instruction observer. No AYXG/native differential comparison. Approved
Protocol.lean is unchanged. Candidate: StageAbstraction.lean.

## Recommended core

- `StageCorrect run admissible postcond`: an admitted input has a result and
  every result satisfies its postcondition. This is availability and result
  correctness, NOT divergence freedom or enumeration of all native executions.
- Reuse `StateFrame`; proved union composition once as `stateFrame_compose`.
- A data-only `FlagsComponents` binds operations/layout once. No proof fields.
- Preparation/loading/capture each state their value, frame and PC effects
  together. Capture retains ORIGINAL post-target state as reference.
- Keep concrete codecs, independent bit layout, classifier and record/separation
  requirements. No generic lens library or assumed setter laws required.

The candidate's `preservesApprovedContract` proves a biconditional with the
existing FlagsProtocolContract. This proves equivalent obligations, not observer
correctness. Both the equivalence and frame composition checked on pinned Lean
on NixOS, source c132261ae7dc1d18ee359c2f4e41863bedca9dbc, exit 0, no sorryAx.
Equivalence axioms: propext, Classical.choice, Quot.sound. Frame composition:
propext. One unused-section-variable warning remains on the frame lemma.
Earlier failed checks exposed reserved identifiers, subsequently fixed; logs
are retained. Command and resource evidence is in evidence/service.txt.

## Measured reduction

Declaration lines (excluding comments/proofs): existing fidelity/frame/PC/
combined contracts 73; generic StageCorrect + data record + input domain + three
stage specs + compact contract 46. About 37% shorter contract presentation.
This is NOT a whole-file reduction: candidate coexists with approved source,
and its equivalence proof adds initial lines. No global optimality claim.

## Further reductions, in priority order

1. Adopt the checked equivalent refactor after human review. Derive existing
   modeled end-to-end assertions from the component contract and frame algebra;
   avoid separately hand-writing those implications for every profile.
2. Define reusable metadata assembler and raw-preserving validity classifier
   as actual Lean helpers, prove their simple laws, and bind real callers to
   those implementations. Do not merely assume arbitrary implementations use
   them. Native event/fault classification is a separate richer operation.
3. Reuse read64-after-eight-byte-writes lemmas to reduce the ~1,400-line
   repetitive GPR Pipeline.lean. Keep independent slot tables, bounds, record
   writer correspondence and architectural layouts explicit.
4. Add projection/support laws for vector aliases only when needed: XMM/YMM
   project from canonical ZMM cells. Whole-field frame permissions alone do
   not constrain upper bits. State expected upper-bit behavior explicitly.

## What must not disappear

- Every successor, not just one good result, must satisfy effects.
- If outcomes later include failure, existence of a classified result is not
  successful-capture availability. Keep success availability and inhabited
  coverage explicit so reject-all implementations cannot pass.
- Every first-stage result must establish the next stage's domain before
  applying a sequencing theorem. Existing stage inputs differ; do not add a
  context-carrying framework solely to make a generic theorem applicable.
- Native faults/aborted prefixes and all-execution termination need actual
  execution binding. A relation that omits bad paths cannot prove safety.
- Fixed/conservative footprints must not be inferred from observed changes.
- Host buffers/ownership/FFI effects and tracee machine state are distinct.
- Saved metadata acquisition and actual invocation/reporting remain concrete
  obligations. Model encoding validity is not architectural observability.

## Review

Astra max /root/abstraction_astra: iterative source review of existing contract,
initial core, exact candidate, equivalence proof, and future-use counterexamples.
Recommended core and exact equivalence; cautioned against premature lenses,
generic sequencing, codec unification and claims of termination from existence.
Parent ran the supplied equivalence proof and frame algebra successfully.
Luna /root/find_frame_reuse found existing AYXG QFAbvStep.compose_denotes_iff,
StateUpdate.eval_compose and WRUH writes_frame; no general Env projection or
read/write-set API surfaced in the bounded search. VTDO provides observation
adequacy rather than a replacement operational frame library.

Design timebox began 2026-11-08 08:43:16 UTC; deadline 08:53:16 UTC.
No approved contract was rewritten or native implementation started.
