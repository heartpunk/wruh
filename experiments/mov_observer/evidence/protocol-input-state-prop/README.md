# Input state frame obligation validation

Source: c1775ee9c2550d3a08ddcbe0c550abc5adc39f3a.

ProtocolInputStateFrame is an unproved Prop. No theorem, axiom or sorry was
added. It frames preparation plus loading, independently of target/capture
success, relative to the current extracted context. Existing proofs unchanged.

## Typecheck

NixOS service wruh-input-state-prop-20261107 exited 0. Full Protocol.lean
checked from committed snapshot with usable Git metadata. Exact command,
compiler store path and resource measurements: service.txt. Output: typecheck.log.
Reused unchanged compiled dependencies documented in
../protocol-input-memory-frame/README.md. Typechecking verifies the statement
is well typed, not that the obligation holds.

## Astra light source review

Agent /root/review_input_state_prop; gpt-6-astra, low reasoning. Read-only,
no builds. Verdict: pass, no concrete blockers.

The exclusion list contains exactly memory, RIP and sixteen GPRs. Universal
typed variable quantification covers every other field in the current context.
input_enables_loader supplies a successor for every wanted/ambient pair, so
the premise is nonvacuous. No target/capture success or preservation assumption
is required. Preparation retains the environment tail; loadUpdate copies the
remaining fields and memory. The separate memory conjunct confines changes to
inputWrites. The obligation is feasible and explicitly model-scoped.

Reviewed Protocol.lean lines 61–84, Pipeline.lean lines 9–13 and 1415–1432,
and models/InputModel.lean lines 23–117 at the source revision above.
