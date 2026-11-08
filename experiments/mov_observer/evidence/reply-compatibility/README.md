# Request/reply compatibility checkpoint

Source: `eecedf7d91db59483616d267da378a4bd5e989d1`.

Added `OperationReplyCompatible` and `CallReplyCompatible` in `Bridge.lean`.
These require correct reply constructors, originating stop/process identity,
full success lengths, and bounded failure transfer counts. They do not prove
kernel execution, transferred contents/effects, error causality, freshness,
or termination. The latter remains a separate existing obligation.

Integrated remote Lean 4.34.0 check passed on NixOS, unit
`observer-spec-eecedf7d.service`, beneath `fleet-build.slice`, 2 GiB memory,
zero swap, one CPU. Checked Protocol, ContractEquivalence, NativeBoundary,
Bridge, Wire, Transfer, VectorProtocol, LegacyFp, FaultProtocol, WholeObserver.
The existing VectorProtocol unnecessarySimpa warnings remain unchanged.
Exact source snapshot included Git metadata; no remote source edits.

Terra 6.1 high, in-process agent `/root/review_reply_terra`, performed a
read-only source review and found no concrete blocker in this narrow obligation.
It confirmed matching shapes/counts with NativeBoundary, Wire and Transfer,
and explicitly did not attest the separate execution/freshness/causality goals.
No build was performed by the reviewer. No observer implementation or proof
was added. None of the four full specification chunks is claimed complete.
