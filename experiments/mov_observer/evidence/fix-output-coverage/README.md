# Fix 5: whole-observer output completeness

Base: 33d9bcd730b6872bbea8db7b0f0aedf7914de62d.
OutputCoverage requires the request's selected record to retain exactly the
fixed output quotient's distinctions and to recover its class. This requirement
is unconditional. ObserverOutputComplete additionally binds each actual observed
record to the original stop in the same execution history, with exact selected
values and quotient recovery. ObserverCoreContract now includes it.
These are obligations, not proofs or a new observer implementation. Capture
availability and other deferred audit findings are not repaired in this change.

NixOS Lean 4.34.0 typechecked NativeBoundary, Bridge, Transfer, VectorProtocol,
LegacyFp, FaultProtocol and WholeObserver sequentially, exit 0. Only two existing
unnecessarySimpa warnings in VectorProtocol occurred. The accompanying script,
log and resources preserve the source hash, AYXG revision and execution details.
