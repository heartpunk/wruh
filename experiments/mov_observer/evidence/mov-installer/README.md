# Historical restricted MOV loader certificate — withdrawn

**Withdrawn in `2adf40f32915734033491e98e2e1a3a5251bd206`.** The theorem below
assumed requested memory was already installed. Its proof and positive review
did not establish the requested installer. This file preserves historical
evidence, not a current completion claim.

Base: 10474a4c9b9c96f4e19608b14d2fcf42ffb19e2b.
MovInstaller.lean SHA-256:
a9a435d7c67ded8d78aec73975441c80c8f25991f079fb7c5a648abead54c351.

`mov_installer_contract` proves InstallerContract for the existing exact
sixteen-MOV loader model and existing preparation. It reuses `load_input`,
`input_installed`, `input_enables_loader`, `loader_preserves_mem` and `writes_frame`.
The modeled remaining fields are preserved by the extracted update itself.
The generic standard in Bootstrap.lean is unchanged.

Input quotient: all sixteen GPRs, target PC, every memory byte outside the
private input slots. Admission requires PC 0x400170 and wanted/ambient memory
agreement outside those slots. It does not claim arbitrary-memory installation.
Other modeled fields are preserved. Native privacy of the slots, capture,
ABI correspondence and the complete observer are outside this certificate.
The q/recover arguments are unused capture-profile parameters, not hypotheses
asserting a correct capture implementation.

NixOS Lean 4.34.0 validation passed on 2026-11-09. Remote snapshot includes Git
history; typecheck.log records source hashes and cached AYXG revision
324752afe80b05d7fd8854834725cf5ee360f173. Unit observer-mov-instance-4.service,
invocation 0faeb07bd9cb46829b045f41579401df, user heartpunk, fleet-build.slice,
2 GiB memory, no swap, one CPU, TasksMax=64, LEAN_NUM_THREADS=1.
Peak memory 772128768 bytes; CPU 45220714000 ns. Exit 0.
The theorem's printed axioms are only propext, Classical.choice, Quot.sound.
Earlier local-source revisions needed elaboration fixes and the preservation
proof needed a local heartbeat allowance; no failed revision is claimed valid.

Astra Max reviewed the concrete scope and proof, finding no blockers. Review
was source-only; the coordinator ran the remote check. check_pipeline.sh now
includes MovInstaller after Bootstrap; shell syntax validation passed. The
full unrelated observer suite was not rerun.
