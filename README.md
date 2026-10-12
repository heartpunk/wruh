# Wruh

tl;dr: it extracts [ayxg](https://github.com/heartpunk/ayxg) models, which are represented as symbolic transition systems. the extraction has been proven to yield models bisimilar to the emulation of the symex engine provided, conditional on the engine satisfying fairly standard definitions of symex per the literature. exact requirements are stated in the theorems, but are intended to be consistent with [Voogd et al., “Denotational Semantics for Symbolic Execution”](https://doi.org/10.1007/978-3-031-47963-2_22) ([one of the author's bibliography entries, which links to a preprint!](https://ebjohnsen.org/publication/23-ictac/)) and [the Rocq formalization thereof](https://github.com/Aqissiaq/ICTAC-DenotSymbEx/tree/submission).

ayxg models give a few useful affordances:

- you can backwards slice and compose to get an smt-lib translation of any straight line execution path of the binary
- you can prove over 'em in lean, as there's a lean embedding
- the lean embedding has a region algebra if ur into that
