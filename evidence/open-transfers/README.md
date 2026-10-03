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
//extractor:open_transfers_smoke`. Execution evidence pending.

The provider-selected path retains manifest/CFG pin checks and optional external
models. Generic extraction requires no provider. Open transfers are not closed
callee semantics; no fabricated return or unconstrained callee is supplied.
