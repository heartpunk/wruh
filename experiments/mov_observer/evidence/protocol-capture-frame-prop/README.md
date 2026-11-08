# Capture/handoff frame obligation validation

Source: c6d74ef3e5e1f10b7eafa7819bd25c8cbad7df9e.

ProtocolCaptureHandoffFrame is an unproved Prop. No proof, axiom or sorry
added; existing proofs unchanged. It frames the completed modeled endpoint
against the original post-target state before RIP redirection.

## Typecheck

NixOS unit wruh-capture-frame-prop-20261107 exited 0. Protocol.lean checked
from the committed snapshot with usable Git metadata. Exact invocation,
compiler path and resources: service.txt. Full output: typecheck.log.
Unchanged cached dependencies are documented in
../protocol-input-memory-frame/README.md. This establishes well-typedness,
not a proof of the new obligation.

## Astra light source review

Agent /root/review_capture_frame_prop; gpt-6-astra, low reasoning.
Verdict: PASS, no blockers. Read-only; no builds or edits.

Both field and memory equalities compare with original post. Only memory
and RIP are exempted fields. handoff_enables_capture supplies an endpoint
for every post, so the premise is nonvacuous. Handoff only replaces RIP;
captureUpdate preserves other typed fields, and CaptureSpec.framed provides
the existing memory frame. No hidden fidelity assumptions or extra
preconditions. Comments accurately limit the obligation to completed modeled
endpoints, excluding intermediate-prefix/native-fault claims.

Reviewed Protocol.lean lines 85–103; Pipeline.lean lines 1433–1448;
models/Extracted.lean lines 452–543; Proof.lean lines 79–102 at source above.
