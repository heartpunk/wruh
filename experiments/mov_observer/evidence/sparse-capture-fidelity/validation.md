# Sparse memory capture validation

## Scope and revisions

Wruh source was checked at parent commit `2f62f17106e89210a68f06ccf8f96d7eb097c111` in sibling workspace `wruh-sparse-capture-fidelity`. The AYXG dependency was checked at the Wruh flake-pinned commit `324752afe80b05d7fd8854834725cf5ee360f173`. Lean was 4.34.0, compiler commit `293d5d0c0c3f3dded4688b3ccd6a33939ac5102b`.

The change factors the existing requested-range read loop through `readRequestedMemory` and `withReadback`. `runtime_readback_image_fidelity` constructs a one-range `SparseMemoryImage` for any returned region and proves each in-bounds requested index is represented at `region.address + i` with that readback byte. The existing `readMemory` helper rejects a short transfer. The theorem uses its exact-length condition and the nonwrapping range condition already checked by `makeElf`; it does not assume that the target preserved the input payload. Each sparse range remains arbitrary in size. The theorem is per region; it is not a proof of the whole IO loop.

The current `readRaw` returned-content behavior is accepted as a trusted kernel/FFI boundary for this stage. The Lean proof does not implement or verify kernel read behavior.

## Lean validation

On NixOS, the full `experiments/mov_observer/check_pipeline.sh` run completed successfully in systemd child `wruh-sparse-capture-fidelity-20261110-final-check` (exit status 0), with 12 GiB memory, 2 GiB swap, and 200% CPU limits. The transferred source's proof SHA-256 matched the checked source: `9837deaca419029ae1e188cff739ca298a95423d6efc344b8a18e9375ac4cef2`.

A direct check of the same module with cached dependencies also succeeded in `wruh-sparse-capture-fidelity-20261110-module-only` (exit status 0; 15.933 s; peak 836.5 MiB; no swap), under a 4 GiB memory, 1 GiB swap, 200% CPU limit.

The separate `#print axioms` audit succeeded in `wruh-sparse-capture-fidelity-20261110-axioms` (exit status 0; 4.211 s; peak 366.3 MiB; no swap), under a 2 GiB memory, 1 GiB swap, 100% CPU limit:

```text
'MovObserver.SparseCaptureFidelity.runtime_readback_image_fidelity' depends on axioms: [propext, Classical.choice, Quot.sound]
'MovObserver.SparseCaptureFidelity.runtime_region_address_preserved' does not depend on any axioms
```

No `sorry`, `admit`, `native_decide`, or declared axiom occurs in `SparseCaptureFidelity.lean`.

## Native smoke evidence

The native build succeeded on NixOS. The default `run.sh` sequence passed 12 scalar and 6 FP observations, then the vector preflight returned `vector trials require XSAVE`. `vectorLayout` returns `none` when CPUID leaf 1 ECX does not expose both XSAVE bit 26 and OSXSAVE bit 27. The diagnostic now names both bits; no vector or xstate behavior changed.

The existing smoke runner was then invoked with `OBSERVER_TRIALS="trials fp-trials fault-trials"`; it passed 12 scalar observations, 6 FP observations, and 4 fault observations, including partial REP effects. Vector execution was unavailable on this NixOS CPU/VM. No vector behavior is claimed validated.

## Source hashes

```text
9837deaca419029ae1e188cff739ca298a95423d6efc344b8a18e9375ac4cef2  experiments/mov_observer/SparseCaptureFidelity.lean
0372711c006af0aa76c7a4c3e73e2082d9a282d8f0962a436a1522a3a8d137e4  experiments/mov_observer/native_observer/Observer.lean
490cb064e9845841180ea28c6bdd5b9c93f6abe91966cf415721d3186ab301a6  experiments/mov_observer/check_pipeline.sh
a4b6b29d4a7487b34b623fc1e4cf573fffff4210d9953c8c0685407bd90bf3fe  experiments/mov_observer/native_observer/VectorTrials.lean
09cd58651f67231bfcf99e4f9e2c10320c4c94f91a885de65cfea682da6608d0  experiments/mov_observer/native_observer/README.md
```
