# Installation coverage validation

Base: d45519200dba16cf3d58b3a7ae49d64e0b0643d3 plus this commit's Bootstrap.lean change.
Reviewed and typechecked source SHA-256:
6af2af54f3e6e969f054154e2a4bd2eab27c2a6700de1a677b914554b1d35701.

NixOS Lean 4.34.0 typecheck passed without diagnostics on 2026-11-09.
Remote snapshot preserves Git metadata; typecheck.log records the base and the
modified source hash. AYXG: 324752afe80b05d7fd8854834725cf5ee360f173.
Unit observer-coverage-6af2af54.service, invocation
d312f7a0d81448bab9a1043d265d8b5d, user heartpunk, fleet-build.slice,
2 GiB memory, no swap, one CPU, TasksMax=64, LEAN_NUM_THREADS=1.
Result success, exit 0; resources.txt records peak memory and CPU time.

Astra Max source review found no blockers: coverage matches the approved
implication, is conjoined into InstallerContract, and the same fixed inputQ is
threaded through AccessFrameObligations and AccessToBootstrap. Capture, MOV,
framing and the underlying BootstrapObligation are unchanged. The existing
installation availability obligation remains required. Reviewer did not build.

Props only. No new proofs or observer implementation.
