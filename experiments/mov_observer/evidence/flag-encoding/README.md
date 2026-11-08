# Flag encoding correction validation

Checked source: 9747718f36b851d5df850ca69611991dc00ff109.
NixOS wruh-flag-encoding-20261107 exited 0. Full Protocol.lean typechecked
using the same cached dependencies documented in
../protocol-input-memory-frame/README.md. Snapshot retains Git metadata.
Exact command and resource evidence: service.txt; diagnostics: typecheck.log.
No new theorem proofs or axioms. Typechecking is not a conversion proof.

Terra 6.1 reviewer /root/review_flag_encoding, medium reasoning, read-only:
PASS. D +1/-1, AC/ID 0/1 and nine bit positions agree with VEX
fd41c675d50845b0aadd0b42ac7490038e2f3d82, pub/libvex_guest_amd64.h:73–87
and priv/guest_amd64_helpers.c:919–970. Encoder preserves unmodeled bits
and rejects invalid encodings. Reviewer performed no builds or edits.

The conditional valid-post premise does not implement invalid-successor
reporting. The eventual Lean orchestrator must establish invariant preservation
or explicitly report invalid outcomes; silently filtering them is prohibited.
Python remains calibration scaffolding, not the target orchestrator. The goal
remains the Lean executable, concrete ABI bridge and harness end-to-end proof.
