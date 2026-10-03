# Architecture-derived AMD64 state

Source baseline: `26f628ad545b858b72453bc1ac4fdcd7d555a31e`.
Validated implementation: `0d8b8d6abd61937dc9faf13063b169bbd4162635`.
Subsequent validator-only correction `28553183` rejects an empty candidate set.
All source changes were local; frozen snapshots ran on Linux through the
repository Nix/Bazel wrapper and configured REAPI profile. No candidate binary
was executed natively.

## Representation

The installed angr 10 AMD64 architecture supplies 88 backing regions and 352
register views. The STS has 91 declarations: 84 backing regions, six canonical
arithmetic flags, and byte-addressed memory. `cc_op`, `cc_dep1`, `cc_dep2`, and
`cc_ndep` are engine flag thunks, explicitly normalized to the six flag bits;
they are not additional independent architectural state. No `artificial` filter
is used. Vector 512-bit backing, x87 backing, FS/GS, rounding fields, masks,
segments, and modeled control fields are included.

Aliases are slices of backing declarations. The artifact records the complete
architecture layout, IP/SP views and endianness. The corpus runner validates
that layout against its declaration domain. Older fixtures without layout are
explicitly identified as `legacy-projection`.

Finite selector replay happens only when the engine reads a selector:

- Direction `d`: `1` or `2⁶⁴−1`, the VEX encodings of forward/backward.
- SSE/x87 rounding: all four VEX rounding encodings `0..3`.
- x87 `ftop`: all eight low 3-bit cases, preserving the remaining 29 raw counter
  bits symbolically. This is not whole-counter concretization or a quotient.

A reported symbolic-rounding default causes extraction failure rather than an
approximate STS. An unexpected within-instruction symbolic selector or symbolic
register offset is rejected explicitly rather than guessed.

## Checks and commands

Frozen frontend `/tmp/wruh-architecture-0d8b8d6a` on NixOS:

```sh
nix develop --no-write-lock-file --command scripts/bazelw build --config=reapi \
  //extractor:architecture_state_check //extractor:architecture_runner_check
nix develop --no-write-lock-file --command scripts/bazelw build --config=reapi \
  //extractor:corpus_native_models
nix develop --no-write-lock-file --command scripts/bazelw run --config=reapi \
  //extractor:angr_upgrade_parity -- --state-extension \
  --baseline /tmp/wruh-cpython-base-26f628ad/bazel-bin/extractor \
  --candidate /tmp/wruh-architecture-0d8b8d6a/bazel-bin/extractor \
  --output /tmp/wruh-architecture-0d8b8d6a-projection.json
```

The corpus model target is explicitly materialized before comparison; REAPI
`toplevel` download otherwise need not retrieve intermediate models.

- Focused checks PASS: alias views, metadata round-trip, EAX zero extension, AH
  preservation, XMM write/upper-vector preservation, FS/GS parametric loads,
  flag COPY normalization, eight x87 counter partitions preserving full
  increment, four SSE/four x87 rounding-store partitions, and both direction
  encodings with disjoint guards.
- All six existing O0/O2 alias/overlap/division models extract successfully.
- 384 deterministic STS-only executions match independent formulas from the
  exact audited C functions: return value and all 32 storage bytes. Counts are
  executions; some input tuples repeat the same observable input for a function.
- 196 baseline guard/state/target mismatch queries are UNSAT across those six
  models, proving preservation of the prior state projection on this corpus.
- Final build exit 0;41.852s wall time. See retained actual build log for exact
  timing/action counts. Comparator exit 0 with six nonempty per-model reports.

`comparison-inputs.tar.gz` retains exact baseline and candidate model artifacts
and their SHA256 checksums. The models include binary hashes, CFGs and extraction
inputs. The JSON reports and logs are retained alongside it.

## Limits

This exports angr's modeled AMD64 state, not a claim that angr implements all
physical AMD64 semantics. In particular VEX's x87 model and hardware exception/
NaN-payload fidelity remain engine/FP-track concerns. No FP arithmetic test is
claimed here. The focused checks validate representative instructions and
selector partitions, not every ISA instruction. No full CPython model or native
end-to-end campaign is claimed. Corpus extra-register initial values are stated
model-harness choices; comparison observes RAX and storage, not otherwise
unobserved native register contents. The old projection checks do not establish
new-field semantic correctness beyond the focused checks.
