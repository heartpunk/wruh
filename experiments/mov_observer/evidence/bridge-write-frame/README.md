# Allocation and write-frame specification increment

Source: 16bc829c5c48ecf1b1c207b7672193db20892adf.
NativeBoundary.lean and Bridge.lean typechecked on NixOS with Lean 4.34.0,
using Protocol from 474813899b9a01768924704941c1c2e353099fee and the existing
pinned observer dependencies. Exit 0; resource record attached.

Terra 6.1 targeted review passed: generations and retired incarnations,
state-indexed scratch disjoint from input/output, explicit write membership and
input-write exclusion address the previous increment's issues. Actual concrete
write/allocation trace completeness is still a required execution-binding
obligation, not established by this specification or its typecheck.

This is an incremental chunk-1 checkpoint, not completion. Next: operation
transfer/error semantics, actual ABI layout binding, and whole-orchestrator
finite execution. No observer implementation/proofs or native comparison added.
