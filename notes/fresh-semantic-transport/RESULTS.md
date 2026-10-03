# Checked universal semantic transport

## Revisions and ownership
- Isolated workspace: /Users/sophiesmithburg/workspaces/wruh-fresh-semantic-transport
- Bookmark: fresh-semantic-transport; baseline de5491ceeb46.
- Checked source: 4142bd2d7cc529157566a257200e5eda5cd5d063.
- AYXG source: 179342d8a0b63dcdea34c4db45cd29a04ca782f0, voogd-symbolic-step.
- Snapshot SHA256: e23c8910364c404384feab1f05223661d8df967de4058610744955c4e5bd1da2.
- No push or merge. Subsequent evidence commit changes documentation only.

## Exact achievement
FreshExtraction.extract calls the adapter step function on each fresh input, resolves ordered bindings into guarded dense complete-state transformers, and assembles ordinary AYXG STS transitions. extract_transport proves equality with independent adapter.emulate under the four explicit SymexLaws; extract_bisimulation derives strong identity bisimulation. AyxgSymex.laws discharges all four laws for existing AYXG source semantics and its Voogd stepper. AyxgSymex.recovers and bisimilar quantify over every supported AYXG STS, with no recovery hypothesis. CONTRACT.md records all premises; source contains complete statements.

## Linux checks
Command, in the WRUH frozen snapshot with WRUH_AYXG_SOURCE pointing to the recorded AYXG snapshot:
```
nix develop path:/tmp/ayxg-lean-fresh-transform-05d140bc --command bash -c 'lake build Wruh Wruh.FreshTransformExamples Wruh.FreshExtractionExamples && lake env lean notes/fresh-semantic-transport/ProofAudit.lean'
```
Exit 0. Six new bounded examples cover actual extracted swap evaluation, empty output, duplicate alternatives, identity cycles, disabled edges, and arbitrary-model bisimulation. Fourteen retained transformer examples cover ordered dependent reads, aliasing/write order, simultaneous updates, guards, byte loads/stores and wraparound, and metadata. Examples supplement the universal theorem, not substitute for it.

All five audited theorem constants depend only on propext, Classical.choice and Quot.sound. FPInterpretation is an explicit semantic parameter, not a hidden implementation correctness assumption. Initial two example builds failed on list indexing elaboration; these were fixed locally and the full command rerun. The core transport and instance proofs passed their first build unchanged.

## Resources and reproducibility
NixOS VM; physical Entrapta CPU 33°C before execution (high79°C, critical89°C). Source staged via git archive from owning clone, no remote source edits. Detached user systemd unit wruh-transport-verified-20261003: MemoryMax=4G, MemorySwapMax=0, CPUQuota=400%, AllowedCPUs=2-5, TasksMax=256; LEAN_NUM_THREADS=4. Journal: 11.358s wall, 9.830s CPU, 439M peak. Exit file records 0. Completed transient unit was garbage-collected before show: resources.txt's defaults are not the actual launch limits; journal.txt retains accounting. Launcher and logs retained alongside final thermals.

## Limits and next step
Output sharing via ShareCommon.shareCommon'; no peak-allocation bound. Dense updates, not sparse syntactic change lists. No production Python/angr correspondence, exchange, CLI or hookup proved or implemented here. Independently reviewed source boundary: REVIEW.md.

Revisit notes/fresh-transform-core/PLAN.md with the user before any next tranche. Next proposed work is operational correspondence with fresh.py and its called helpers; do not begin automatically.
