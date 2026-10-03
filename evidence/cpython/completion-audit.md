# CPython-lifting goal: evidence and remaining work

All three tracks are integrated and committed. Evidence below supports the selected-function and bounded validation scope; inherited scalar SSE rounding fidelity is explicitly deferred by user decision (WRUH #1).

| Requirement | Authoritative evidence | Status |
|---|---|---|
| Dedicated workspaces/baselines; no push/merge | Architecture/calls/AYXG workspaces and local integration bookmark; documented baseline26f628ad | Complete locally |
| Preserve checker separation and angr upgrade | Reconciled base26f628ad; extraction/compose retained, checker absent | Integrated |
| Derive complete modeled AMD64 backing/aliases | architecture-state c9eb996c, independent review; 88 regions/352 views/91 declarations | Complete AMD64 scope |
| Replace inventories/serialize layout/affected runner | architecture-state implementation and focused checks | Complete |
| Exact selector handling and flag normalization | Focused checks; no symbolic rounding defaults; ftop high bits retained | Complete modeled domains |
| Preserve old projection | 196 UNSAT baseline mismatch queries; repeated after committed FloatLib-backed AYXG pin, evidence/cpython/floatlib-pin-old-projection.json | Complete tested corpus |
| Exercise aliases/vector/TLS/flags/selectors | Focused checks and 384 STS-only corpus executions | Complete bounded checks; TLS dependence only |
| Admit indirect/tail/external/cross-object transfers | open-transfers b8344447; reviewer accepted corrections | Complete tested boundaries |
| Pin objects/relocations/image/provenance | Two-object fixture; exact32/64/COPY extents; skippedTLSDESC16; fail-closed unknowns | Complete supported ELF cases |
| Equality partitions/complement without invented returns/stubs | Supported controls plus self-call test, independent review | Complete bounded controls |
| Python FP sorts/operations/codec/DAG/Z3/interpretation | AYXGf27e3824; supported fp_test/z3_test pass, evidence/cpython/floatlib-ayxg-pin-tests.log | Integrated/tested Python |
| Lean FP types/eval/substitution/laws | AYXG0d279809; all12 core modules typechecked; evidence/cpython/ayxg-fp-lean-core.log; fresh read-only review found no blocking defect | Core checked; committed 9,419-comparison cross-language campaign passed |
| FloatLib RNA support | 222236f0 removes non-IEEE sqrt fallback; scoped kernel proofs and1,020 operational comparisons pass | Corrected IEEE checks and expanded1,305 FloatLib/Z3 fixtures pass; evidence in AYXGf27e3824 |
| Canonical Python/Lean/Z3 FP correspondence | AYXG979131d0 committed actual lean.py FFI evidence: 9,419 comparisons,34 families,3 formats,all5RMs,69 explicit corners; exit0 | Complete bounded correspondence campaign; independent reviewer inspected committed979 evidence and accepted69 corner fixtures |
| Exact extraction CPython closure/build | identity.json and each successful action runtime trace; hashes/build match | Complete |
| Real CPython integer/memory/dynamic-transfer STSes | Three full compressed artifacts,23/82/191 edges; fresh independent review | Complete selected-function scope |
| Real CPython arithmetic FP STSes | float_add/float_mul full artifacts committed; actual binary64 fp_add/fp_mul nodes; patched exporter20UNSAT | Extracted and independently audited; inherited unconditional SSE RNE gap deferred under WRUH #1 |
| No candidate native execution | Probe treats ELF inputs as data; fixture compilation/static loading only | Maintained |
| Final committed integrated evidence | Current local integration, interim evidence and pins committed | Passing logs/artifacts committed; final AYXG546f2948 metadata pin accepted by independent reviewer; rounding repair deferred |

No whole-interpreter composition, physical x87/NaN-payload/exception fidelity, dynamic-linker execution, initialized interpreter state, or release claim follows from these checks.

## Approved exporter repair completed

ANGR_NIX `52f1b96515da7fbe5059e3251fd603acf56deb2b` builds pinned angr 10.0.1 source with four `mantissa + 1` SMT export corrections, upstream-required grpcio-tools 1.80 wheels, and declared angr-data. WRUH `b02dac78` declares the Nix-built package as its Bazel pip repository override and checks all four conversion forms at binary32/binary64. These checks executed successfully against the rebuilt package:20UNSAT, including eight conversion checks. Frozen snapshots retain earlier logs; no candidate native execution occurred.

## Final supported preservation run

WRUH943bd1c9, AYXG24f6686b runtime, angr-nix52f1b965: all five CPython selections, six prior corpus models, architecture and transfer controls built successfully through configured REAPI. Baseline26f628ad projection comparison:196 obligations, allUNSAT (`patched-angr-old-projection.json`). Public exporter checks:20UNSAT including eightFP conversions (`patched-angr-exporter-checks.log`). This proves the exercised old projection; it does not resolve upstream hardware rounding fidelity. See `upstream-sse-rounding-gap.md`.

## Final dependency handoff

AYXG546f294843d8c78c72895b68287081f45cc1b55b retains the tested semantic sources and committed9,419-comparison evidence from979131d0. Its only additional changes are portable FloatLib source-key/Lake manifest metadata and associated evidence. Qualified Lake metadata checks passed on NixOS; independent review accepted the handoff. WRUH stages this exact committed revision. No push or merge occurred.

Inherited scalar SSE rounding is deferred, not abandoned, by explicit user decision: https://github.com/heartpunk/wruh/issues/1. Non-RNE hardware equivalence is not claimed.
