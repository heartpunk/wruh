# Generic binary function census

The Bazel executable `//extractor:binary_census` is reusable: point it at an ELF executable or shared object and provide a target identity, version, and output directory.

```sh
nix develop --command bazel run //extractor:binary_census -- \
  --binary /nix/store/.../libexample.so \
  --target-id example \
  --target-kind generic \
  --target-version 1.2.3 \
  --output-dir /tmp/example-census
```

For an interpreter, set `--target-kind interpreter` and `--target-implementation`. Run it in the repository's Nix development shell so Bazel can resolve the pinned angr and AYXG sources.

## Inventory boundary

The initial policy enumerates defined, sized ELF `STT_FUNC` symbols in the main object loaded by angr. Symbols sharing one entry address are one candidate; the largest declared extent wins, then the lexically first symbol name, while all aliases are retained. Candidate identifiers use the object's relative virtual address. The runner currently targets AMD64 ELF and records unsupported architectures as a census-level inventory failure.

This is an auditable binary-symbol inventory, not a claim to find anonymous functions, source-level functions without ELF symbols, code in dependent shared objects, or dynamically generated code. For the three interpreter jobs, the selected object is Lua's shared library, QuickJS's `qjs` executable, or CPython's `libpython` shared library. Nix builds those artifacts with stripping disabled.

## Reports

Each run writes:

- `census.jsonld`: BFE + PROV-O graph for the binary/image, build and inventory provenance, candidates, attempts, outcomes, failures, interruptions, and open external-call boundaries.
- `summary.json`: candidate and outcome counts, first-observed failure-stage/code categories, and report/archive digests.
- `entries.jsonl`: a flushed ledger row per completed attempt, so interrupted runs retain completed work.
- `progress.json`: atomic partial counts refreshed every 100 candidates.
- `function-artifacts.tar.gz`: one canonical FreshFunction JSON artifact per successful candidate.

Per-function CFG or extraction errors are preserved as `bfe:FailureObservation`; timeout and memory exceptions are `bfe:Incomplete` with interruption observations. The process continues to later candidates after per-function failures. A runner-level interruption leaves the flushed ledger and most recent progress checkpoint as partial-run evidence. If interrupted while writing the tar stream, the archive may be unreadable; the workflow uploads available files with `if: always()`. Each job has a six-hour runner timeout.

## GitHub jobs

`.github/workflows/binary-census.yml` runs three independent top-level jobs (`lua`, `quickjs`, `cpython`) on GitHub-hosted `ubuntu-24.04` for every pull request. Each job builds its pinned, symbol-preserving target from `flake.lock`, runs the generic Bazel target, and uploads its report bundle as a 14-day artifact. No interpreter census is run on the developer workstation.

