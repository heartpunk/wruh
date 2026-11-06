# Native instruction differential campaign

This is a draft. Read [STATUS.md](STATUS.md) for tested components, coverage
limits, and remaining incomplete cases before interpreting results.

The campaign reads every row of `data/iform-catalogue/catalogue.jsonl` and
validates the seed and each structured mutation with iced-x86 and the catalogue
XED helper. Each changed encoding receives an existing WRUH extraction; that
relation is reused across generated concrete inputs. Hypothesis chooses inputs
without solving SMT queries. The launcher requires a finite-memory, finite-CPU,
finite-task and finite-swap cgroup and runs the native helper only inside bubblewrap. It captures
two writable pages, one read-only instruction page, and up to two additional
zero-initialized writable pages required by the instruction.

On Linux x86-64, build the runner and campaign with:

```sh
nix develop --command bazel build //corpus:native_step_runner //extractor:native_catalogue_campaign
```

Build the catalogue's XED helper in its pinned `tools/iform_catalogue/shell.nix`
environment. Supply absolute paths for that helper, bubblewrap, the native
runner, and every required Nix store runtime closure (repeat `--runtime` as needed). The runner's dynamic
loader and libraries can be inspected with `ldd`. Run inside an explicitly
bounded fleet child cgroup and retain both the output log and Hypothesis
storage directory. Replay databases are separated by iform and seed encoding. For example, with the paths and a full immutable revision
set in the environment:

```sh
set -o pipefail
export HYPOTHESIS_STORAGE_DIRECTORY="$PWD/.hypothesis"
bazel run //extractor:native_catalogue_campaign -- \
  data/iform-catalogue/catalogue.jsonl \
  --xed "$XED_HELPER" --bwrap "$BWRAP" --runner "$RUNNER" \
  --runtime "$RUNTIME_CLOSURE" --source-revision "$WRUH_REVISION" \
  --examples 4 --row-seconds 30 | tee native-campaign.log
```

Each row runs in a disposable worker with its own deadline; a timed-out
worker is stopped before the next row, and its latest generated input is logged
when available. A row is `MATCH` only if all attempted native comparisons
match and no attempted case is incomplete; invalid generated bindings are
reported separately. `INCOMPLETE` includes unsupported state, address,
decoding, model, and timeout conditions. `MISMATCH` retains the shrunk input;
`ERROR` reports infrastructure failures. The command returns nonzero for a
mismatch, infrastructure error, or no successful comparisons. The run header records
the supplied revision, source-file fingerprint, catalogue and executable
hashes, CPU and runtime context, and Hypothesis storage location. A supplied
revision is a declaration; the fingerprint identifies the actual files used.

The native PBT GitHub Actions workflow partitions the ordered catalogue into
128 disjoint shards, with every row assigned to exactly one job. Each job
retains its campaign log and Hypothesis replay database. A failed or incomplete
row is retained as a coverage gap; unsupported cases do not become matches.
Definite mismatches, infrastructure errors, or a shard with no successful
comparisons fail the job. The 30-second row
deadline bounds each row, not the total campaign. Replay or shrinking can
execute more than the nominal four generated examples. Each row also attempts
one native comparison of its exact observed encoding. Invalid generated
bindings are rejected by Hypothesis and recorded, not counted as generated
examples or successful native comparisons. If valid generated examples cannot
be produced, the row remains incomplete even when its seed matched.
