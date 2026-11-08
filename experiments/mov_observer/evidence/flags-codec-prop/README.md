# Flags conversion obligation validation

Source: 8069ee24b34898e4ab3fa817f375942760984a5c.
FlagsConversionCorrect is an unproved Prop; no proof or axiom added.

NixOS unit wruh-flags-codec-prop-20261107 exited 0. Full Protocol.lean
checked from committed snapshot including Git metadata. Invocation and
resources: service.txt; diagnostics: typecheck.log. Unchanged cached imports
are documented in ../protocol-input-memory-frame/README.md.
Typecheck establishes well-typedness, not correctness of the conversions.

Terra 6.1 /root/review_flags_codec_prop, medium reasoning, source-only review:
PASS, no blockers. Four clauses cover canonical decoding, valid-input encoding
success with exact model roundtrip and unmodeled-bit frame, full original-word
decode/patch roundtrip, and rejection iff invalid. No vacuous success condition.
The nine fields occupy distinct bits, with bounded values and canonical d/ac/id,
so inspection found no apparent feasibility blocker. No builds or proofs run.

Roundtrip laws alone do not establish architectural bit-layout fidelity:
consistent permutations could satisfy them. Independent architecture mapping
remains separate; the prior conversion review checked the actual layout against
pinned VEX source. No claim of native OS installability or full RFLAGS coverage.
