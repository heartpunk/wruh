# Per-request ownership contract scope

Source: `61167d217d646151c266b75d5821563745a6710b`.
CallReplyCompatibleFor specializes the existing reply condition to one request.
CallReplyCompatible retains the original global quantification. OwnedCallContract
now uses the same request as its wire, lifetime, frame and termination clauses.

Terra 6.1 high /root/review_reply_terra identified this overconstraint during the
stopping audit and verified the exact correction, source-only. It found no
independent increment that would complete a whole chunk without resolving the
pending state/fault/environment and concrete execution-boundary decisions.
This is not a completion claim for any chunk, nor a reason to defer routine
compatible implementation details to user approval.

Integrated Lean 4.34.0 check passed on NixOS:
Protocol, ContractEquivalence, NativeBoundary, Bridge, Wire, RuntimeOwnership,
Transfer, VectorProtocol, LegacyFp, FaultProtocol, WholeObserver.
Unit observer-spec-61167d21.service, child of fleet-build.slice, 2 GiB/no swap/
one CPU. Existing VectorProtocol style warnings remain. Exact committed Git
snapshot, no remote source edits. No observer implementation/proofs added.
