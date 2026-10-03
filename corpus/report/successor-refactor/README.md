# Successor stepping validation

Source baseline: `dc38d2d3a5e36e400af3974188dbb977ddd06965`.
Prior successful corpus evidence: `6ae1484ca1ed9d26291e1290d4a6a69d7a7ef181`.
Stepping implementation: `7c3de9eab77689d3dd3c6d098d82f35cf5da3ebd`.
Pinned corpus run: `3dc999c036611201ac4b75610221ffa70634fc55`.
AYXG: `d516978f538e90c58ad547ecfb76a6db44d5623f`.

23 selected variants PASS; seven variants intentionally unselected.
Both alias, overlap, and division variants PASS. Division O0/O2 each
contains two terminal-error edges. Strict CFG overlap validation remains.

All 19 prior PASS models are identical after only these universal semantic
identities: unsigned BV x <= maximum is true; conjunction associativity,
commutativity and true elimination; double-negation elimination. No changes
to updates, targets, occurrences or edge counts. Exact ELF hashes checked.
`baseline-comparison.json` records each comparison. This is semantic evidence
by exact algebraic identities, not a separate SMT solver run or native test.

Commands on frozen NixOS snapshots:

```
WRUH_GHOT_ROOT=/tmp/ghot-handler-equiv-4097a20e nix develop --command scripts/bazelw build --config=reapi //extractor:corpus_zeroth_all
python3 corpus/compare_baseline.py /tmp/wruh-corpus-results-6ae1484c /tmp/wruh-corpus-results-3dc999c0
```

Snapshots: `/tmp/wruh-corpus-7c3de9ea`, `/tmp/wruh-corpus-3dc999c0` on NixOS.
Local full outputs: `/tmp/wruh-corpus-results-7c3de9ea`,
`/tmp/wruh-corpus-results-3dc999c0`. Earlier diagnostics preserved unchanged.

Limits: this checks local instruction STS extraction, not composition or
native end-to-end behavior. Fault edges are preserved even if infeasible for
a particular instruction/entry restriction. No candidate binary executed.
The collector's VEX feature walk remains static coverage instrumentation;
the extractor's outcome reconstruction has been removed. Static CFG discovery
still reads VEX exits, with division faults excluded from ordinary traversal.
