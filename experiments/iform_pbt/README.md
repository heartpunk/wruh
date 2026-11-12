# Native instruction PBT

This campaign samples occurrences from the #87 JSONL catalogue with Hegel.
For each sampled occurrence it builds an ELF containing the exact bytes,
extracts its model once with `wruh-fresh`, and compares multiple generated
states against native execution. GPRs, defined arithmetic flags, direction
and control flags, vector registers, masks, SSE rounding, and the generated
memory image are compared. The native execution runs in Bubblewrap.

On x86-64 Linux, from the Wruh root inside its Nix development shell:

```sh
lake build wruh-fresh wruh-iform-pbt
experiments/iform_pbt/run.sh /path/to/catalogue.jsonl /path/to/work 10 2 190717990
```

The last three arguments are the occurrence budget, samples per occurrence,
and Hegel seed. The work directory holds the current stub and model and the
Hegel failure database; keep it to replay failures. Set
`WRUH_PBT_TIMEOUT_SECONDS` to change the 300-second whole-run timeout.

The runner prints matches, mismatches, incompletes, and errors separately; a
run with no comparisons fails. Control-flow instructions, native faults,
unavailable model inputs or outputs, and modeled memory accesses outside the
generated image are reported incomplete. The comparison covers the generated
memory image; full-process memory and x87 fidelity are separate work.
