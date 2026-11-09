# Named installer/capturer contract validation

Base: `83788fef3e69f0180b5981942e1a548fd402b664` plus this commit's Bootstrap.lean change.
Reviewed/typechecked source SHA-256:
`064337b9d44376c1325836c5733595c69d538878877e1a37986cdef0e6df3483`.

NixOS Lean 4.34.0 typecheck passed without diagnostics on 2026-11-09.
Remote snapshot includes usable Git metadata; the base and modified source hash
are recorded in typecheck.log. AYXG: `324752afe80b05d7fd8854834725cf5ee360f173`.
Unit `observer-named-064337b9.service`, invocation
`0b4ca9c977bd4e239df2c338c162443b`, ran as heartpunk under fleet-build.slice,
2 GiB memory, no swap, one CPU, TasksMax=64 and LEAN_NUM_THREADS=1.
Result success, exit 0, memory peak 420495360 bytes, CPU time 4000549000 ns.

Astra Max source review found no blockers. It confirmed that:
- InstallerContract requires requested input equality, concrete boundary values,
  and preservation; boundary values cannot inspect the resulting loaded state.
- movProfile still requires the same requested GPRs, fixed RIP and initialized
  memory as before the replacement of the entry predicate.
- CapturerContract retains complete quotient recovery of the original post-state.
- The named contracts still support the existing component/bootstrap implication.

Scope: proposition definitions only, no new proofs or observer implementation.
Architecture coverage is supplied by the fixed profile, not inferred here.
