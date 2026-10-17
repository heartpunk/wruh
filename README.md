# Wruh

Wruh extracts symbolic transition data from [AYXG](https://github.com/heartpunk/ayxg) models and produces the corresponding artifacts.

## Proven correspondence

`Wruh.FreshExtraction.Adapter.reference` is an idealized, source-indexed `SymbolicTransitionSystem Unit Γ Edge`. Its symbolic executor returns successors that retain both the original edge label and the complete composed QF_ABV guard/update step. `SymexLaws` states the exact contract: for each edge label and complete source/target environment, a returned successor denotes a transition precisely when that labeled transition belongs to the reference system.

`extract_bisimulation` proves a label-sensitive strong bisimulation between the extracted system and the reference system. It matches the exact original edge label and relates the complete `Config Unit Γ` states. `Unit` is the structural control component; machine control such as the program counter and error flags lives in the ordinary typed environment `Γ`. `OutcomeLaws` can additionally require each retained edge's site, target, fault/recovery event, and error-state update to agree with those environment fields. `extract_bisimulation_and_outcomes` combines that state/outcome contract with the bisimulation.

`Wruh.AyxgSymex` proves the adapter laws for AYXG's source-indexed QF_ABV transition systems. The theorem is about this idealized provider contract; it does not prove that an external Angr implementation satisfies the contract.

`Wruh.FreshTransform` has a separate job: it closes ordered temporary reads and constructs the guarded simultaneous update used by extraction. Its local denotation theorem is distinct from the transition-system bisimulation.

The proof's assumptions are stated in the theorems and follow the symbolic-execution semantics of [Voogd et al.](https://doi.org/10.1007/978-3-031-47963-2_22) and the [Rocq formalization](https://github.com/Aqissiaq/ICTAC-DenotSymbEx/tree/submission).

AYXG models also let you:

- backwards-slice and compose a straight-line execution path into SMT-LIB;
- prove properties in Lean through the typed embedding;
- use the region algebra for finite-state exploration.
