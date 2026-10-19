# Wruh

## human overview

tl;dr: it extracts [ayxg](https://github.com/heartpunk/ayxg) models, which are represented as symbolic transition systems. the extraction has been proven to yield models bisimilar to the emulation of the symex engine provided, conditional on the engine satisfying fairly standard definitions of symex per the literature. exact requirements are stated in the theorems, but are intended to be consistent with [Voogd et al., “Denotational Semantics for Symbolic Execution”](https://doi.org/10.1007/978-3-031-47963-2_22) ([one of the author's bibliography entries, which links to a preprint!](https://ebjohnsen.org/publication/23-ictac/)) and [the Rocq formalization thereof](https://github.com/Aqissiaq/ICTAC-DenotSymbEx/tree/submission).

ayxg models give a few useful affordances:

- you can backwards slice and compose to get an smt-lib translation of any straight line execution path of the binary
- you can prove over 'em in lean, as there's a lean embedding
- the lean embedding has a region algebra if ur into that

## ai generated shit

### Proven correspondence

`Wruh.FreshExtraction.Adapter.reference` is an idealized, source-indexed `SymbolicTransitionSystem Unit Γ Edge`. Its symbolic executor returns successors that retain both the original edge label and the complete composed QF_ABV guard/update step. `SymexLaws` states the exact contract: for each edge label and complete source/target environment, a returned successor denotes a transition precisely when that labeled transition belongs to the reference system.

`extract_bisimulation` proves a label-sensitive strong bisimulation between the extracted system and the reference system. It matches the exact original edge label and relates the complete `Config Unit Γ` states. `Unit` is the structural control component; machine control such as the program counter and error flags lives in the ordinary typed environment `Γ`. `OutcomeLaws` can additionally require each retained edge's site, target, fault/recovery event, and error-state update to agree with those environment fields. `extract_bisimulation_and_outcomes` combines that state/outcome contract with the bisimulation.

`Wruh.AyxgSymex` proves the adapter laws for AYXG's source-indexed QF_ABV transition systems. The theorem is about this idealized provider contract; it does not prove that an external Angr implementation satisfies the contract.

`Wruh.FreshTransform` has a separate job: it closes ordered temporary reads and constructs the guarded simultaneous update used by extraction. Its local denotation theorem is distinct from the transition-system bisimulation.
