# Native observer specification — unfinished

This is obligations-only work. No new observer implementation or observer proof
has been authorized. Typechecking and targeted reviews are recorded under
`evidence/`; they do not establish completion of the four requested chunks.

| Chunk | Current concrete statements | Remaining specification work |
|---|---|---|
| Lean/ABI/native boundary | NativeBoundary.lean, Bridge.lean, Wire.lean, RuntimeOwnership.lean, Transfer.lean: exact GPR mapping, concrete request/reply frames, originating-request reply compatibility, distinct IO-error/malformed returns, finite call obligation, allocation lifetime, actor-authorized reference rights and raw-return handoff, write footprints, logical memory prefixes | Concrete runtime accessor/object-layout and ownership-event binding; exact operation semantics/error decisions; complete source/native trace binding; explicit external progress and memory stability premises |
| FP/vector | VectorProtocol.lean: all current ZMM/mask fields, independent byte record, stage fidelity/frames/separation. LegacyFp.lean: lossless legacy image and known fields | Full x87/MXCSR model correspondence, FP installation/capture stages, full feature-profile integration. Legacy image is not upper-vector capture |
| Faults | FaultProtocol.lean: frozen original evidence, finite returned fields, prefix recoverability and no-replay fallback. WholeObserver.lean: ordered same-process phases, target exits/unavailable outcomes, matching native/IO/malformed failure evidence and exact preceding wait receipts | Real stop classification, failure causality, stop-token lifecycle, cleanup/disposal and fault-specific visibility |
| Composition | WholeObserver.lean: same-request input fidelity, ordered target occurrence, whole-run finite completion, finite returned observation, same-execution prefix frames and bridge reply/outcome receipt linkage | Link actual concrete component executions, fixed inhabited coverage/admission and conditional availability, whole-observer host/native effects and cleanup |

## Pending user decision

Full FP fidelity requires information absent from the current modeled FP state.
Question sent: extend modeled state with lossless raw x87 payloads and missing
control/status fields while retaining and relating current modeled fields?
No such representation change has been made or presumed approved.

A second question is pending: use an explicit effect-program representation
interpreted by the Lean orchestrator, or prove a separate operational model
faithful to ordinary Lean IO code? The former is proposed; neither proof route
has been treated as approved. No interpreter implementation has started.

## Boundary discipline

Do not omit actual executions to make an abstract relation satisfy these Props.
Do not treat instrumented event names as proof of their provenance/completeness.
Do not assume bridge, decoder, frame or failure correctness as an external law.
Do not use a model prediction as native input evidence or output evidence.
Do not infer full coverage from the legacy image, a typecheck, or a targeted review.
Binding decisions must preserve contract AND telos. Routine compatible details
remain autonomous; material changes or unresolved compatibility need user judgment.

## Review handoff: what the remaining decisions change

Audit source: `61167d217d646151c266b75d5821563745a6710b`.
The latest integrated check and Terra review are in `evidence/request-scope/`;
ownership review and corrected runtime binding skeleton are recorded in
`evidence/runtime-ownership/`.
No full chunk is complete. In particular, `ObserverCoreContract` is not yet the
requested end-to-end native-observer obligation.

1. **Lean/ABI boundary.** Read `Bridge.CallTerminates`, `CallBufferLifetime`,
   `CallDynamicMemoryFrame`, `CallReplyCompatibleFor`,
   `RuntimeOwnership.OwnedCallContract`, and the exact `Wire.*Correct`
   definitions. They constrain all abstract call paths and exact bytes. They
   do not yet relate `ForeignAPI.invoke` to those paths. The pending effect-program
   versus ordinary-IO decision determines the concrete relation and compiler/runtime
   preservation statements. Recommendation: an explicit effect program shared by
   the interpreter and its semantics, with project-owned interpreter/FFI correctness
   as obligations, never as imported foundations. This is not authorization to
   implement that interpreter.
2. **FP/vector state.** Read `VectorProtocol.VectorContract` and
   `LegacyFp.DecoderCorrect`. Full modeled vector bits have installation/capture
   obligations; the legacy FP image has exact byte preservation. There is no full
   x87 conversion, installation or capture obligation yet. The pending representation
   decision is whether to extend AYXG-facing state losslessly and relate the existing
   fields, rather than discard raw 80-bit payloads. Recommendation: extend it, subject
   to user judgment. Raw transport evidence is not a second replacement semantics.
3. **Faults and environment.** Read `FaultProtocol.FaultCaptureSafety`,
   `FallbackCorrect`, and `WholeObserver.TransportEvidenceLinked`. Original evidence
   and state recovery are constrained, without target replay. Still to settle:
   which stopped outcomes have a required complete observation, what to return for
   an intervening external signal or process exit, and how cleanup is permitted to
   affect an owned tracee after evidence is secured. Recommendation: preserve raw
   wait/siginfo evidence for every outcome; do not infer successful instruction
   completion from SIGTRAP alone. Their concrete policy and total obligations remain to be specified; routine
   compatible details do not require a new approval. Only material uncertainty or
   changes to fault observability, ownership, or progress require user judgment.
4. **Whole-observer domain and availability.** Read `ObserverCoreContract` and
   `CaptureAvailable`. The latter is not currently included under a concrete
   independently fixed admission/environment premise. We must settle the required
   CPU/OS-enabled state and target-visible mappings, including whether memory is
   proved private/stable or concurrent external writes are modeled. Recommendation:
   establish private stable observation storage from containment rather than silently
   assuming a stopped process has stable memory. Any exclusions from the target
   domain require user judgment. External primitive progress must be stated
   explicitly; project-owned loops, retries and calls must still terminate.

## What implementation does and does not block

The intended total contracts, concrete state relations, effect semantics, resource
ownership rules and failure classifications can be specified before implementing
the observer. Pending decisions block only the definitions materially dependent on
them. In particular, pinned runtime ABI investigation and representation-neutral
shared-execution linkage can proceed now. Missing implementation is not an excuse
to leave those statements as arbitrary predicates.

Exact compiled bridge/stub bytes, symbol addresses, compiler-produced layouts and
the correspondence of a particular executable's transitions to the specification
require those artifacts to exist. Their future obligations must still be declared
with explicit artifact parameters and fixed semantics; proving or instantiating
those obligations belongs to implementation/proof work. No code-hash placeholder
or user-approved foundation may stand in for our own glue's correctness.

## Decision-dependent stopping audit

The reviewed independent ownership quantifier correction is complete. Terra's
source audit found no remaining independent increment that would complete a
whole requested chunk. More abstract linkage could be written, but would not
resolve the concrete component-boundary, state, fault and environment choices.
Do not label any chunk complete or silently select narrower coverage.

Four questions have been presented to the user: lossless x87/state extension;
Lean effect-program versus ordinary-IO proof route; required observation for
interruptions/exits and owned-tracee cleanup; private/stable versus shared or
device-backed memory. No answer has been presumed. Runtime OOM/abort behavior
must additionally be reconciled with the chosen external resource/progress
premises; returned IO.Error handling does not solve that problem.

This is a stopping point for dependent specification work, not a claim that
all possible source inspection or abstract schemas are exhausted. Resume with
concrete definitions under the agreed decisions, preserving the accumulated
obligations, rather than treating their current projections as trusted laws.
