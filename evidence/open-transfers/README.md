# Open transfers implementation

Baseline: 26f628ad545b858b72453bc1ac4fdcd7d555a31e.

Ordinary CLI: `extract --artifact ELF --root SYMBOL --output bundle.json`.
Optional `--candidate-root SYMBOL` provides additional discovered indirect targets.
Optional `--objects objects.json` is a JSON list of `{path, sha256, base_addr}`
records. CLE automatic dependency searching and SimProcedure substitution are
both disabled. No binaries are natively executed.

The bundle retains exact local summaries and open targets; bounded composition
routes admitted target addresses under explicit equality guards and retains the
complementary symbolic exit. Returns keep the existing guarded call-continuation
logic. Loops remain in raw local STSes; bounded composition can still exhaust its
bounds, which is not a semantic verdict.

`loaded_image` is separate initialization data: per-object hashes, mappings,
segment bytes and permissions, relocation resolution. Undefined relocation byte
ranges override segment data; CLE synthetic extern addresses are not known
initial values. The image is never baked into parametric instruction memory.
Consumers must explicitly choose/apply initialization; this tranche does not
implement dynamic-linker startup/TLS allocation, IFUNC resolution or syscalls.

Per-instruction provenance uses each root's containing object's SHA-256.

Focused validation target: `nix develop --command scripts/bazelw run
//extractor:open_transfers_smoke`. Execution PASS in integrated frozen revision 5d8e79e6 on NixOS/REAPI; full action invocation a754ad7e-065f-4b12-902f-5c4cbf678248 exited 0 in45.646s.

`open_transfers_check.json` proves target-partition completeness/disjointness,
3 open admissions/3 strict rejections, no-candidate preservation, tail routing
and external poststate. `open_object_check.json` records two pinned loaded ELF
objects, resolved cross-object relocation,5 extracted roots including the real
PLT thunk,24 local edges and per-object provenance. No candidate native execution.

The provider-selected path retains manifest/CFG pin checks and optional external
models. Generic extraction requires no provider. Open transfers are not closed
callee semantics; no fabricated return or unconstrained callee is supplied.
