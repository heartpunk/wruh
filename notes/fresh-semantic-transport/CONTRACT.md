# Universal fresh extraction contract

Recorded before implementation. Workspace `/Users/sophiesmithburg/workspaces/wruh-fresh-semantic-transport`, bookmark `fresh-semantic-transport`, baseline `de5491ceeb46`. Read-only AYXG `179342d8a0b63dcdea34c4db45cd29a04ca782f0`. Foreground owns only this new workspace.

The adapter supplies source sites, independent whole-source and per-site emulation relations, fresh symbolic input states, and a symbolic step function. The driver invokes that step function for each source site, applies retained `FreshTransform.transform` to its before/after observations, and assembles an ordinary AYXG QFAbvSTS. Metadata is retained in a tagged intermediate. Ordered temporary read bindings are interpreted by the existing transformer.

Contracts (none mentions extract):
- Source coverage: whole-source transition iff some enumerated site's input guard admits the state and its independent per-site relation transitions.
- Fresh input: its substitution evaluates to the original valuation wherever its guard holds.
- Primitive soundness: each admitted returned outcome has an admitted input, its before snapshot equals the supplied input substitution under that same valuation, and its after snapshot is a concrete per-site successor. Read bindings are evaluated in order before its guard/after expressions.
- Primitive completeness: each per-site concrete transition from an admitted represented input has a returned outcome with that admitted guard and exact target under the same valuation.

Main theorem, for arbitrary Program, Site, Metadata and AYXG context, and any FPInterpretation:
`SymexLaws adapter → ∀ program source target, (extract adapter program).toLTS.canStep source target ↔ adapter.emulate program source target`.
Also prove both directions of strong identity bisimulation on complete states.

Reference instance: Program = existing AYXG QFAbvSTS; sites = its steps; independent emulation = existing toLTS.canStep; per-site emulation = existing edge.denotes; input = identity/true; symbolic stepping = AYXG symbolicStep on the singleton source edge. Prove every contract field, then obtain recovery for every AYXG STS. No supplied response transcript, binary-discovery claim, Python correctness/hookup claim, or ISA correctness claim. Existing QFAbvSTS finite symbolic representation imposes no bound on concrete state count or loop executions.
