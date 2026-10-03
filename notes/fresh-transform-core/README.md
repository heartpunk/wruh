# Retained fresh transformer core — clean continuation

This workspace contains observation types and local transformer helpers/proofs only. It does not contain a Lean extraction driver or a universal extraction theorem.

## Isolation and provenance

- New workspace: `/Users/sophiesmithburg/workspaces/wruh-fresh-transform-core`.
- New bookmark: `fresh-transform-core`; foreground-owned.
- Parent: `e49b212f14bd0c86e617c8808c8c6fda1f76c64c` (`cpython-integration`), before both collector code and its design notes.
- Selectively retained declarations from WRUH `1abb093fee9aef19387e20665b164f570da030d7`.
- Supported AYXG dependency for checking: `179342d8a0b63dcdea34c4db45cd29a04ca782f0` (`voogd-symbolic-step`). No AYXG modifications.

## Retained

- `Wruh.Observation.ResolvedOutcome` and `Outcome`: typed before/after state, guard, ordered read bindings, metadata.
- `Wruh.FreshTransform`: guarded transformer construction, read binding resolution, byte-memory helpers and their local preservation proofs.
- `Wruh.FreshTransformExamples`: the existing 14 focused examples.
- Minimal existing Lake/toolchain configuration. Namespace/import changes only, plus terminology corrections in comments; transformer definitions and proof bodies are retained unchanged.

## Excluded

No `FreshControl`, `Response`, collector `State`/`Next`/`Error`, `start`/`next`/`accept`, `FreshAssembly`, `Collects`, collection invariant, or transcript-based `driver_transport`. None of their commits is an ancestor of this continuation. Old implementation/report bookmarks remain historical evidence, not the continuation design. Their claims of completing the intended universal driver transport were incorrect.

## Actual remaining target

WRUH's fresh extraction algorithm must be proved against source/emulation semantics via the agreed symex laws, with AYXG's Voogd stepper as the Lean reference engine. Local observation preservation is only a helper. Inverted control through Python is allowed. Persistent/rebase remain excluded. No further driver implementation is authorized by this cleanup.

## Validation and review

PASS on NixOS: `lake build Wruh Wruh.FreshTransformExamples`, then `lake env lean notes/fresh-transform-core/ProofAudit.lean`, inside the pinned AYXG Nix environment. Existing 14 examples and five theorem audits passed. No new tests or semantics were added. Local/remote Lean source hashes match; obsolete plan/collector/assembly commits are verified absent from ancestry. See evidence files.

One read-only Luna reviewer confirmed the retained type fields, definitions, theorem statements/proofs and examples are unchanged except namespaces/imports and comment terminology. No obsolete collector dependency remains. No reviewer builds or edits.

Final execution: 15.280 seconds wall, 15.912 seconds CPU, 710.1 MiB peak. Detached `wruh-core-r1` on NixOS with MemoryMax=4G, MemorySwapMax=0, CPUQuota=400%, AllowedCPUs=2-5, TasksMax=256 and LEAN_NUM_THREADS=4; existing fleet reservations checked first. Entrapta CPU was 29°C before launch (79°C high/89°C critical). Execution reused the idle prior Lake root, moving obsolete staged Lean source files to `/tmp/wruh-retired-collector-20261003` before applying the frozen snapshot; no cache deletion, copied build outputs or remote source edits. Other workspaces and old bookmarks were not rewritten.

Reproduce from this checkout with AYXG at the recorded revision:

```sh
export WRUH_AYXG_SOURCE=/absolute/path/to/ayxg
nix develop path:/absolute/path/to/ayxg --command lake -R update ayxg
nix develop path:/absolute/path/to/ayxg --command lake build Wruh Wruh.FreshTransformExamples
nix develop path:/absolute/path/to/ayxg --command lake env lean notes/fresh-transform-core/ProofAudit.lean
```

No push or merge. Only core isolation is complete. See `PLAN.md` for proposed follow-on work; none of it is authorized by this cleanup.
