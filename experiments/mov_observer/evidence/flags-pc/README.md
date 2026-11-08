# Flags endpoint PC obligation validation

Source: 7737bdb7bbcccbf38ae8d078bb3e2925520162f6.
Prop only, integrated with same stage functions in FlagsProtocolContract.
NixOS wruh-flags-pc-20261108 exited 0. Full Protocol.lean checked from committed
snapshot with Git metadata. Command/resources: service.txt; output: typecheck.log.
Same pinned compiler/cache as flags-separation check.

Terra6.1 /root/review_flags_pc, medium reasoning, read-only: PASS.
Four endpoint-PC requirements, shared functions and validity domains agree.
Fidelity supplies existence on these domains; disabled stages cannot satisfy
the combined contract. Handoff forces captureEntry=4194304 as in enterCapture.
No blocker or excessive constraint found. No intermediate-step, termination,
exactly-once target, or saved-PC correctness established. No proof/build by
reviewer. FlagsMemorySeparation approved by user before this increment.
