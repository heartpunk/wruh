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

Validation pending. No push or merge.
