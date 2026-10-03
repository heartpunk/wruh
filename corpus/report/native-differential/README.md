# First end-to-end native differential evidence

**560/560 MATCH; zero MISMATCH, zero INCOMPLETE.**
Two optimization levels; alias, overlap and division; return and every one
of 32 storage bytes. 176 deterministic cases plus 384 Hypothesis-generated
cases (64 per function per optimization). Comparison phase: 54.714 seconds.
Native candidates executed only after explicit user approval and within
verified namespaces/cgroups. No push or merge.

Baseline: `c2eae4715c1e`. Runner/model extraction: `7f4815f45eda`.
Launcher/campaign: `9ff7c9aab71d`; supported artifact-label correction and
execution audit: `9ff4ee029bfb`. AYXG: `d516978f538e`.
Exact native binary hashes: `../../native/build-audit.json` and enforced in
`../../native/sandbox.py`. All six model hashes match the corresponding ELF.
Model outputs: `/tmp/wruh-native-models-7f4815f4` locally; reproducible via
`//extractor:corpus_native_models`.

Full inputs, native stdout/stderr/exit/launch commands, STS traces and both
outputs: `results.json.gz` (lossless; digest in `results-manifest.json`).
Summary: `summary.json`. No failing examples were dropped or excluded.
`first-build.log` preserves the initial Bazel artifact/sidecar ambiguity;
`final-build.log` preserves its corrected run. Frontend service consumed
2 min 8.692 sec CPU over 2 min 2.724 sec wall time, approximately 1 GiB peak
memory under the 8 GiB cap. No OOM or resource failure reported.

## Reproduce

On NixOS with the frozen local snapshot and pinned AYXG staged:

```
WRUH_GHOT_ROOT=/tmp/ghot-handler-equiv-4097a20e nix develop --command scripts/bazelw run --config=reapi //extractor:native_differential -- --output=/tmp/wruh-differential.json
```

This command executes the audited candidates; it requires the standing
explicit approval, exact binary hashes, the pinned runtime store paths,
working user-systemd and verified Bubblewrap namespaces. It fails rather
than falling back to unsandboxed execution. See `../../native/EXECUTION.md`.
The foreground launch uses a detached user-systemd service with resource
limits as recorded there; configured compilation/extraction uses REAPI.

`sandbox-verification-final.json` records actual distinct namespaces,
read-only mount flags, zero capabilities, no-new-privileges, loopback-only
network, absent home/workspaces and writable disposable /tmp. Effective
service settings: 256 MiB memory, zero swap, one CPU, 64 tasks, two seconds.
`verify_sandbox.py` uses the trusted Nix Python closure plus candidate libc
closure solely for the probe; native candidates mount only their exact
four-store-path libc closure. The probe requires staging `sandbox.py` as
`/tmp/wruh-sandbox.py` and its queried trusted Python closure list as
`/tmp/wruh-trusted-python-closure.txt`. It never invokes candidate code.

## Limits

Evidence covers these three compiled functions and audited uint32-derived
inputs, not arbitrary binaries, all architecture state, or full WRUH
coverage. The STS runner starts at each function's ABI entry and interprets
extracted local edges to a return sentinel using AYXG; it does not execute
angr as its runtime oracle. Updates are simultaneous. Initial registers and
flags not supplied by the ABI are zero; private stack/default memory are
zero. Native stack addresses differ, and these functions do not expose them.
Only return and the 32-byte storage are observations; harness/libc startup,
stack scratch bytes, and final flags are not compared. Division hardware
fault outcomes are not exercised by this input domain; zero denominator
takes the source-level branch. No claim of exhaustive verification.
