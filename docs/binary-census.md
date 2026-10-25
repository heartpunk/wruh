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

## Deterministic sampling

By default the runner attempts every candidate in the inventory. To opt into sampling, pass both `--sample-seed` and `--sample-percentage`:

```sh
nix develop --command bazel run //extractor:binary_census -- \
  --binary /nix/store/.../libexample.so \
  --target-id example \
  --target-kind generic \
  --target-version 1.2.3 \
  --output-dir /tmp/example-census \
  --sample-seed release-check-2026 \
  --sample-percentage 5
```

The percentage is a finite decimal from 0 through 100, inclusive. The selected count is `floor(candidate_count * percentage / 100 + 0.5)`, so exact half-candidate ties round upward; 0 selects none, 100 selects all, and an empty inventory selects zero. The runner ranks candidates by the SHA-256 digest of the versioned domain prefix `wruh-binary-census-sample-v1\0` followed by length-prefixed UTF-8 seed bytes, the raw 32-byte binary SHA-256 digest, and length-prefixed UTF-8 candidate ID bytes. It selects the requested count with the lowest digest bytes, breaking digest ties by candidate ID. This does not depend on Python's random implementation.

Sampling metadata (`seed`, the requested decimal percentage, selected count, and policy identifier) is recorded in `summary.json` and `progress.json`. The full inventory is still recorded. Each unsampled candidate has a `bfe:CensusEntry` with `bfe:NotAttempted` and no extraction attempt; it is not removed from the inventory or reported as excluded.

## Inventory boundary

The initial policy enumerates defined, sized ELF `STT_FUNC` symbols in the main object loaded by angr. Symbols sharing one entry address are one candidate; the largest declared extent wins, then the lexically first symbol name, while all aliases are retained. Candidate identifiers use the object's relative virtual address. The runner currently targets AMD64 ELF and records unsupported architectures as a census-level inventory failure.

This is an auditable binary-symbol inventory, not a claim to find anonymous functions, source-level functions without ELF symbols, code in dependent shared objects, or dynamically generated code. The pinned census targets are Lua's shared library, QuickJS's `qjs` executable, CPython's `libpython` shared library, Apache HTTP Server's `httpd` executable, Node.js's `node` executable, and Bun's `bun` executable. Apache is recorded as a generic binary; Lua, QuickJS, CPython, Node.js, and Bun are recorded as interpreters. Nix builds these artifacts with stripping disabled.

## Reports

Each run writes:

- `census.jsonld`: BFE + PROV-O graph for the binary/image, build and inventory provenance, candidates, attempts, outcomes, failures, interruptions, and open external-call boundaries.
- `summary.json`: candidate and outcome counts, first-observed failure-stage/code categories, and report/archive digests.
- `entries.jsonl`: a flushed ledger row per completed attempt, so interrupted runs retain completed work.
- `progress.json`: atomic partial counts refreshed every 100 candidates.
- `function-artifacts.tar.gz`: one canonical FreshFunction JSON artifact per successful candidate.

Per-function CFG or extraction errors are preserved as `bfe:FailureObservation`; timeout and memory exceptions are `bfe:Incomplete` with interruption observations. The process continues to later candidates after per-function failures. A runner-level interruption leaves the flushed ledger and most recent progress checkpoint as partial-run evidence. If interrupted while writing the tar stream, the archive may be unreadable; the workflow uploads available files with `if: always()`. Each job has a six-hour runner timeout.

## GitHub jobs

`.github/workflows/binary-census.yml` runs six independent top-level jobs (`lua`, `quickjs`, `cpython`, `apache`, `node`, `bun`) on GitHub-hosted `ubuntu-24.04` for every pull request. Each job builds its pinned, symbol-preserving target from `flake.lock`, runs the generic Bazel target, and uploads its report bundle as a 14-day artifact. No census is run on the developer workstation.

The workflow passes the PR number and GitHub PR ID, PR head repository and commit, checked-out commit, repository and server URL, workflow run ID and attempt, workflow name, and job ID as CLI arguments. The JSON-LD graph identifies the PR and commit resources as PROV entities, links the census activity to the workflow attempt, and records the run's PR and commit inputs. Local runs outside GitHub Actions may omit all `--ci-*` arguments. On a GitHub Actions runner, detected through `GITHUB_ACTIONS=true` or standard runner environment markers such as `GITHUB_RUN_ID`, the CLI requires every `--ci-*` provenance argument and fails with an explicit list of missing arguments if the workflow does not pass them. Partial metadata is rejected in all environments.

