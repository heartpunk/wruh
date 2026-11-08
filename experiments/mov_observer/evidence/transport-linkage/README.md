# Same-history transport linkage

Source: `a40341cbf1764c22994ee83975387741272b526a`.

WholeObserver now requires every recorded request/reply pair to satisfy
OperationReplyCompatible. Every targetStop and targetExit must have an exact
matching earlier wait reply in the same Ordered running phase. Exact stop token,
wait status and optional siginfo are retained. Adjacency and stop classification
are not presumed. ObserverCoreContract includes this obligation for every
reachable prefix of the same execution.

Integrated Lean 4.34.0 check passed on NixOS in
`observer-spec-a40341cb.service`, under fleet-build.slice, 2 GiB memory, zero
swap and one CPU. Modules: Protocol, ContractEquivalence, NativeBoundary,
Bridge, Wire, Transfer, VectorProtocol, LegacyFp, FaultProtocol, WholeObserver.
Two pre-existing unnecessarySimpa warnings remain. Source was transferred as
an exact committed snapshot with Git metadata; no remote source edits.

Terra 6.1 high reviewer `/root/review_reply_terra` found no concrete blocker.
Review was source-only. It confirmed Protocol was unchanged and that the new
core obligation does not impose adjacency or classify stops. It also noted:
matching-receipt existence does not establish that it is the actual terminal
wait if other transport events intervene. Lifecycle, causality, and complete
source/native execution binding remain open. No observer implementation or
proof was added; the four full chunks are still incomplete.
