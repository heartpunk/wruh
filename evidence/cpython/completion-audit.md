# CPython-lifting goal: evidence and remaining work

This is an interim audit, not a completion claim.

| Requirement | Authoritative evidence | Status |
|---|---|---|
| Dedicated workspaces/baselines; no push/merge | Architecture/calls/AYXG workspaces and local integration bookmark; documented baseline26f628ad | Complete locally |
| Preserve checker separation and angr upgrade | Reconciled base26f628ad; extraction/compose retained, checker absent | Integrated |
| Derive complete modeled AMD64 backing/aliases | architecture-state c9eb996c, independent review; 88 regions/352 views/91 declarations | Complete AMD64 scope |
| Replace inventories/serialize layout/affected runner | architecture-state implementation and focused checks | Complete |
| Exact selector handling and flag normalization | Focused checks; no symbolic rounding defaults; ftop high bits retained | Complete modeled domains |
| Preserve old projection | 196 UNSAT baseline mismatch queries; repeated after AYXG FP transport, evidence/cpython/fp-transport-old-projection.json | Complete tested corpus |
| Exercise aliases/vector/TLS/flags/selectors | Focused checks and 384 STS-only corpus executions | Complete bounded checks; TLS dependence only |
| Admit indirect/tail/external/cross-object transfers | open-transfers b8344447; reviewer accepted corrections | Complete tested boundaries |
| Pin objects/relocations/image/provenance | Two-object fixture; exact32/64/COPY extents; skippedTLSDESC16; fail-closed unknowns | Complete supported ELF cases |
| Equality partitions/complement without invented returns/stubs | Supported controls plus self-call test, independent review | Complete bounded controls |
| Python FP sorts/operations/codec/DAG/Z3/interpretation | AYXG00e2a211; supported fp_test/z3_test pass, evidence/cpython/corrected-ayxg-fp-tests.log | Integrated/tested Python |
| Lean FP types/eval/substitution/laws | AYXG0d279809; all12 core modules typechecked; evidence/cpython/ayxg-fp-lean-core.log; fresh read-only review found no blocking defect | Core checked; final integrated pin pending |
| FloatLib RNA support | 222236f0 removes non-IEEE sqrt fallback; scoped kernel proofs and1,020 operational comparisons pass | Corrected IEEE checks pass; expanded evidence handoff pending |
| Canonical Python/Lean/Z3 FP correspondence | FloatLib operational fixtures plus Python tests; AYXG cross-language bridge pending | Incomplete |
| Exact extraction CPython closure/build | identity.json and each successful action runtime trace; hashes/build match | Complete |
| Real CPython integer/memory/dynamic-transfer STSes | Three full compressed artifacts,23/82/191 edges; fresh independent review | Complete selected-function scope |
| Real CPython arithmetic FP STSes | float_add/float_mul fail public angr SMT export conversion width | Incomplete; upstream repair question pending |
| No candidate native execution | Probe treats ELF inputs as data; fixture compilation/static loading only | Maintained |
| Final committed integrated evidence | Current local integration, interim evidence and pins committed | Incomplete until Lean/FP lifting/remaining validations finish |

No whole-interpreter composition, physical x87/NaN-payload/exception fidelity, dynamic-linker execution, initialized interpreter state, or release claim follows from these checks.
