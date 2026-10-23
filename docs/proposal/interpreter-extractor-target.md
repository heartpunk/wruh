# Proposal: a generic binary function extraction target

## Decision sought

Build a small reusable *target contract and run harness* around WRUH’s existing per-function binary extraction. Keep target-specific acquisition, inventory, and address semantics in adapters. First exercise the contract against Lua, QuickJS, CPython, Node.js, and Bun without requiring any one runtime to reach a particular completion percentage.

This is a design proposal only. No extraction or end-to-end implementation was run for this proposal.

## What the prior runs establish

Lua and QuickJS demonstrate full inventories with durable per-function status records and large merged artifacts. Their blockers differ materially: Lua’s largest class was CFG call-fallthrough extent handling (209), while QuickJS’s largest groups were static CFG issues (240) and SMT/Z3 issues (138). CPython’s all-symbol run reports 22,741/28,078 extracted, but the primary artifact directory was not recovered in this pass; the Obsidian source explicitly marks recovery as outstanding. It records first-observed failures and warns that fixing an early failure can reveal a later one.

These runs do not share one denominator. The generic target must preserve how each inventory was formed rather than flattening counts into a misleading cross-target success rate. Their common useful shape is: pinned analyzed binary image, explicit target identity, a function inventory, one durable result per candidate, failure evidence, and a merged or per-function artifact that preserves open transfers.

## Proposed components

1. **Binary target lock** — exact upstream revision or package pin, build recipe, compiler/configuration, target OS/architecture/ABI, and reproducible binary hashes. Record every loaded object separately when the target uses shared libraries.
2. **Target adapter** — resolves the runtime distribution, identifies the executable/object set, and supplies target-specific inventory rules. It must not change WRUH extraction semantics.
3. **Inventory manifest** — records raw sized function symbols, aliases, address groups, exclusions and reasons, selected stable function ID, start address, declared extent, and inventory provenance. Define the unit explicitly: symbol, unique entry address, or another policy.
4. **Attempt ledger** — exactly one terminal record per selected inventory item, keyed by image digest plus address/identity. Suggested statuses: `extracted`, `blocked`, `incomplete`, `excluded`, `not_attempted`. Store stage, typed failure code, concise message, log reference, output digest, and elapsed/resource metadata. Resume by ledger key without overwriting completed evidence.
5. **Extraction runner** — invoke the existing WRUH binary CFG/fresh-extraction path one function at a time or in deterministic shards. Every shard shares the same immutable input identity and merges only after duplicate/missing-key checks.
6. **Artifact assembler** — combine successful function bundles without implying that unresolved/indirect calls were solved. Preserve unresolved transfer edges and relocation/runtime boundaries as explicit open edges.
7. **Summary and audit** — derive counts from the inventory and ledger, include stage-specific and first-observed categories, verify unique coverage and artifact references, record host/unit/cgroup/tool revisions, and hash all inputs and outputs.

## Failure vocabulary

Use stable high-level buckets with a retained raw exception:

- inventory/identity: aliases, ambiguous ownership, missing/zero extents;
- static CFG: overlapping blocks, call fallthrough crossing extent, unsupported jump kind, decode gap;
- symbolic execution: unsupported helper/operator, symbolic state shape or register selector;
- SMT/export: sort/width mismatch or unsupported theory;
- relocation/runtime image: unresolved relocation, IFUNC/TLS or missing loaded object;
- resource/infrastructure: OOM, timeout, worker interruption, host/transport/build failure; classify as incomplete, not semantic failure;
- artifact/validation: serialization, missing references, digest/merge inconsistency.

Store both `stage` and `failure_code`. A single mutually exclusive “reason” is useful for the first-failure table, but add optional secondary observations so retries do not erase later discovered blockers.

## Ontology alignment

The first-pass ontology uses PROV-O as its only external ontology and defines a generic binary extraction model: `BuildActivity`, `AnalyzedImage`, inventory policy and candidate identity, inventory-generation activity, per-candidate disposition, extraction attempt, failure/interruption observation, and open artifact boundary. `InterpreterImage` specializes the generic image for interpreter targets. A build activity records build inputs and exact Bazel/Nix tool releases where used, and can generate the binary objects/image or local tool releases. Inventory generation then uses the analyzed image, policy, and exact tool-release entities (including angr and WRUH revisions when applicable) to generate the `FunctionInventory` consumed by a census. The model keeps OWL open-world semantics and leaves status/failure vocabularies extensible. The design and Turtle draft are in [the ontology proposal](ontology/README.md). The [ontology landscape](evidence/ontology-landscape.md) records why the adjacent candidates are considered but not imported. Security classifications remain relevant only when a result makes an actual weakness or attack claim.

## Target interface sketch

A target manifest should provide:

```text
target_id, upstream_revision, package_lock, build_recipe_digest
platform: os, arch, ABI, compiler/configuration
objects: [{role, path, sha256, build_id}]
inventory_policy: source, candidate_unit, alias_policy, extent_policy
roots: [{stable_id, object_id, address, size, aliases[]}]
open_boundary_policy: relocations, indirect calls/jumps, external calls
```

A run manifest should add WRUH/AYXG/angr/Z3 revisions, command, host, bounded execution unit, resource limits, start/end time, shard plan, output hashes, per-stage counts, and ledger schema version. Persist raw diagnostics per function, not only a final console summary.

## Initial adapters and acceptance

Apply this target contract first to Lua, QuickJS, CPython, Node.js, and Bun. Reuse the historical Lua and QuickJS runs as fixtures for manifest/ledger conversion; recover the CPython archive before treating its figures as independently audited. Node.js and Bun start with a source lock and inventory-only dry design; no completion threshold is assumed.

For each target, acceptance is about evidence quality: inventory policy is explicit; every candidate has one status; counts reconcile; hashes identify exact inputs/outputs; a rerun can resume deterministically; resource failures are distinguished from extraction blockers; and open semantic boundaries remain visible. Cross-target comparisons should report the inventory unit and stage breakdown beside every percentage.

## Not in scope

No new symbolic semantics, interpreter-level correctness theorem, whole-process initialization model, dynamic execution, or claim of complete interpreter behavior. This proposal does not implement the runner or start any extraction campaign.

## Evidence

See [evidence index](evidence/README.md). CPython’s source note and collection scripts are copied in [attempt counts](evidence/cpython/obsidian-attempt-counts.md) and [collection scripts](evidence/cpython/collection-scripts.md). Lua and QuickJS primary artifacts remain on MBP at the paths in the index; the proposal preserves exact GUI task IDs, revisions, checksums, and artifact locations rather than copying multi-hundred-megabyte bundles into the repository.
