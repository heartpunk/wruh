# Sparse installer implementation and contract

Base: 66180fb2afd3bead5bc51228495e11cd5c9a80f9.

SparseInstaller extends the existing Lean preparation and extracted MOV loader.
writeRequested performs stores of every requested address from wanted memory.
prepareSparse then reuses prepareInput; sparse_installer_contract proves the
existing InstallerContract for all wanted and ambient states. The fixed input
quotient retains all GPRs and every requested byte. The target PC is the existing
loader's fixed fallthrough boundary, not an arbitrary requested PC. The only
layout premise is disjointness from its reserved GPR input slots.

wantedForImage folds the concrete sparse-array payload into requested memory;
installImage uses exactly the certified prepareSparse + loadUpdate path.
image_bytes_consistent derives payload consistency from range bounds and
nonoverlap. installImage_payload proves every supplied byte is installed, without
an ambient-content premise. installImage_gprs/pc/frame give its register, fixed PC,
and unrelated-state results. prepareSparse_frame proves preparation itself leaves
GPRs and other non-memory/non-PC fields unchanged.

This is executable Lean model-state installation plus proofs, not a native FFI
port. OS mappings, native code placement and native bridge refinement remain
outside these results. No arbitrary native-address support is claimed by them.

Validation: NixOS Lean 4.34.0 with AYXG revision recorded in typecheck.log.
Dependencies were built sequentially by check-dependencies.sh. Focused final
check.sh checked SparseInstaller, exit 0; all printed theorem axioms are only
propext, Classical.choice and Quot.sound. Existing dependency sources changed
subsequently only in explanatory comments. check_pipeline.sh now includes the
new module after WholeObserver; its shell syntax was checked locally. This does
not claim a fresh run of the entire repository check_pipeline.sh.
