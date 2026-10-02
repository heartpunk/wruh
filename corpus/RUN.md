# Zeroth-pass static corpus

Baseline: WRUH `5594bfc1157c180fef1fa4a88f119ca4a0a113af`.
Workspace: `/Users/sophiesmithburg/workspaces/wruh-corpus-zeroth`.
Bookmark: `corpus-zeroth`.
Validated runner revision: `6ae1484ca1ed9d26291e1290d4a6a69d7a7ef181`.
AYXG: `d516978f538e90c58ad547ecfb76a6db44d5623f`.

## Reproduce

Stage AYXG with `scripts/stage-ayxg /absolute/path/to/ayxg` before creating the execution snapshot.
The Mac workspace is authoritative; archive committed source from the owning WRUH clone and separately stage the pinned AYXG archive into the frozen Linux snapshot.

On the qualified Linux frontend:

```sh
WRUH_GHOT_ROOT=/tmp/ghot-handler-equiv-4097a20e \
  nix develop --command scripts/bazelw build --config=reapi \
  //extractor:corpus_zeroth_all //extractor:corpus_scan_O0 //extractor:corpus_scan_O2
```

`WRUH_GHOT_ROOT` is required by the inherited MODULE repository declaration. The corpus tool does not read TinyMemory/provider inputs.

Use `nix develop --command scripts/bazelw info bazel-bin` to resolve outputs. Preserve `extractor/corpus_*.json`, including trace sidecars, then:

```sh
python3 corpus/summarize.py /absolute/path/to/results --output corpus/report
```

Each scan compiles the declared C sources using the pinned runtime's Clang 21.1.8, records the full command, retains ELF bytes as base64, builds CFGFast features, and greedily selects against the observed supported-operation/CFG feature universe. Separate extraction actions skip unselected roots and run inventory, static CFG construction, and `extract_fresh_function` for selected roots. `PASS` refers to fresh extraction, not equivalence or concrete execution.

## Evidence

- Final frozen Linux snapshot: `/tmp/wruh-corpus-6ae1484c` on NixOS.
- Local declared outputs, traces, decoded non-executable ELF files, and build log: `/tmp/wruh-corpus-results-6ae1484c`.
- Source/provenance: `provenance.json`, `templates.c`, `real/`.
- Exact local translator case inventory and unfiltered ast-grep outlines: `supported-cases.json`, `outlines/`.
- Feature matrix and results: `report/coverage.csv`, `report/summary.json`, `report/README.md`.

## Safety and coverage boundary

No candidate was executed natively. Compilation, binary loading/lifting, and symbolic instruction extraction were permitted; candidates are not approved for native execution. The musl sources are exact pinned upstream files with their license, not audited native fuzz targets.

All 633 available angr IROp registry names are retained in scan outputs. Registry availability is not end-to-end acceptance. The selection universe has 62 observed features at O0 and 67 at O2, not all possible backend behavior. Statement/expression tags are observed coverage, not a complete inventory of inherited angr handler implementations.

Canonical operation absence may reflect lowering/normalization rather than absence of the source-level behavior: e.g. extensions can become concatenations. Presence is only occurrence coverage, not semantic validation.

No composition, concrete input execution, alias-address relationship, path feasibility, ABI, FP/vector, or fault-behavior validation occurred. Native harness/input-domain audits and model-vs-binary comparisons are the next pass.

## Prepared compute pane

NixOS session `wruh-corpus`, visual pane 1, socket `wruh-corpus-20261002`, unit `wruh-corpus-tmux-20261002.service`. Allowed CPUs 0–15 of 18, CPUQuota 1600%, MemoryMax 40 GiB, MemorySwapMax 4 GiB. Idle shell; all corpus actions ran through configured Bazel/REAPI. Codex PTY session 20521 is attached. Reattach with:

```sh
ssh -tt heartpunk@nixos 'tmux -L wruh-corpus-20261002 attach-session -t wruh-corpus'
```
