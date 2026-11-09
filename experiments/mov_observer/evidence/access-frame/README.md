# Generic access-to-frame obligation validation

Base: `d4e63a960671ba4893af4e6332874e4ca76e6047` plus the Bootstrap.lean addition in this commit.
Reviewed and typechecked Bootstrap.lean SHA-256:
`7b1de69a5cf3906eb4be909562927a67ed2ea036a890d870f1397ff7ff74a8e5`.

NixOS typecheck succeeded on 2026-11-09 with Lean 4.34.0. The remote snapshot
includes Git history; the log identifies its base and the exact modified source
hash, rather than claiming the base alone contains the addition. Cached AYXG
revision: `324752afe80b05d7fd8854834725cf5ee360f173`.

Unit: `observer-access-7b1de69a.service`, invocation
`15c0e0e0d83e4a749d5e327ec1cae704`, under `fleet-build.slice`, user heartpunk,
MemoryMax=2G, MemorySwapMax=0, CPUQuota=100%, TasksMax=64, LEAN_NUM_THREADS=1.
Journal records successful completion: 4.386s wall time, 4.320s CPU,
399.9M peak memory. See service.log, typecheck.log and check.sh.

Astra Max source review found no blockers. It checked arbitrary-transition
quantification, effectful overlapping views, enabled execution, propagation
through every permitted access effect, inhabited singleton boundary conditions,
and the connection to the same Bootstrap construction and fixed quotient.
The reviewer ran no builds; the coordinator performed the remote typecheck.

These are obligation definitions only. No observer implementation, concrete
architecture instance, composition proof, native validation, or completion of
the separate termination/prefix/ABI obligations is claimed.
