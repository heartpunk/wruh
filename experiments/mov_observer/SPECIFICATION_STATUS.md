# Native observer specification — unfinished

This is obligations-only work. No new observer implementation or observer proof
has been authorized. Typechecking and targeted reviews are recorded under
`evidence/`; they do not establish completion of the four requested chunks.

| Chunk | Current concrete statements | Remaining specification work |
|---|---|---|
| Lean/ABI/native boundary | NativeBoundary.lean, Bridge.lean, Wire.lean, Transfer.lean: exact GPR mapping, concrete request/reply frames, originating-request reply compatibility, finite call obligation, allocation lifetime, write footprints, logical memory prefixes | Actual Lean runtime ABI ownership conventions; exact operation semantics/error decisions; complete source/native trace binding; explicit external progress and memory stability premises |
| FP/vector | VectorProtocol.lean: all current ZMM/mask fields, independent byte record, stage fidelity/frames/separation. LegacyFp.lean: lossless legacy image and known fields | Full x87/MXCSR model correspondence, FP installation/capture stages, full feature-profile integration. Legacy image is not upper-vector capture |
| Faults | FaultProtocol.lean: frozen original evidence, finite returned fields, prefix recoverability and no-replay fallback. WholeObserver.lean: ordered same-process phases, target exits/unavailable outcomes, matching transport-error evidence and exact preceding wait receipts | Real stop classification, failure causality, stop-token lifecycle, cleanup/disposal and fault-specific visibility |
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
The next binding decisions must preserve contract AND telos; changes need user judgment.
