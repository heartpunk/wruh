# Flags record decoder binding validation

Source: aeb2b80c54a2091092f84f08ebf79006f0ae202d.
Prop only; no decoder implementation or proof. FlagsProtocolContract approved
before this increment and unchanged; this new obligation is not yet conjoined.

NixOS wruh-flags-record-20261108 exited 0. Full Protocol.lean checked from
committed snapshot with Git metadata. Command/resources: service.txt;
output: typecheck.log. Same pinned compiler/import cache as flags-contract.

Terra6.1 /root/review_flags_record, medium reasoning, read-only: PASS.
Non-wrap bound is a conjunct and permits final valid base 2^64-8, excluding
2^64-7. read64 accesses offsets 0–7 little endian. Equality holds for all total
model memories; reject-all cannot satisfy it. Native acquisition/read errors,
writer agreement, and unmodeled flags remain explicitly separate. No proof
or build performed by reviewer; typecheck is not proof of the obligation.
