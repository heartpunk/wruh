# Compact contract adoption validation

Checked source: 474813899b9a01768924704941c1c2e353099fee.
Approved baseline: 0985ba2869ed206571f5c4f1fdd179720490affa.

On NixOS, Lean 4.34.0 checked Protocol.lean and ContractEquivalence.lean,
using the existing cached observer dependencies and pinned AYXG environment.
Both preservesApprovedContract and preservesApprovedEndToEnd typechecked;
their axiom reports contain no sorryAx. See typecheck.log and resources.txt.
The job used fleet-build.slice, 2 GiB memory, no swap and one CPU.

Terra 6.1 read-only review verified that the frozen regression declarations
match the approved baseline modulo names, found no semantic weakening, and
passed the final documentation revision. No source-review blockers remained.

This validates preservation of obligations, not correctness of a native
observer implementation. No new observer implementation was added.
