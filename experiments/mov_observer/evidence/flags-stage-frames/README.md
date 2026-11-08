# Flags stage frames validation

Source: 9e8c1a2eaa11a72cbea7d76e01cb339ae0cf0b61.
Prop definitions only, no new proofs/axioms. FlagsConversionCorrect remains
unchanged and pending human review; this addition does not imply its approval.

NixOS unit wruh-flags-frames-20261107 exited 0. Full Protocol.lean checked
from committed snapshot with Git metadata. Invocation/resources: service.txt;
output: typecheck.log. Unchanged compiled imports documented in
../protocol-input-memory-frame/README.md. Typecheck is not a proof.

Terra6.1 /root/review_flags_frames, medium reasoning, read-only: PASS, no
blocker or unintended overconstraint in the completed-endpoint scope.
Preparation can directly install flags. Preparation/loader preserve GPRs and
other non-exempt fields; capture including handoff restores all non-memory,
non-RIP fields relative to original post. Three fixed byte footprints.
Pair with ProtocolFlagsFidelity using identical parameters for availability
and value fidelity. Footprint privacy/separation/minimality, native behavior,
aborted prefixes, and RIP sequencing remain separate obligations. No proof
of satisfiability or implementation binding performed by the reviewer.
