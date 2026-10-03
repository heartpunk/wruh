# Angr 10 prototype — bounded Linux validation passed

Baseline WRUH: 0317c362b3854b43a487febbf79d122ddfbc07d6.
Baseline angr-nix: 6baaa779759d00e2b180850dcebb77ed5231dcc9 (angr 9.2.214).
Candidate angr-nix: ca288bef3145174ae8385004e2cbcf6caabb9a76 (angr 10.0.1).
AYXG: c6ea1b57efacc8a567bcaa2ae89af9120aeb2820 (Z3 5.1.0).

Stage using scripts/stage-angr-nix ANGR_NIX_CLONE_ROOT and
scripts/stage-ayxg AYXG_CLONE_ROOT, from the owning clones. No push required.

The new public interface bundles Rust Claripy in angr. Standalone claripy and
BackendZ3 no longer exist. WRUH now imports from angr and exports a result
equality using public Solver.to_smt2(), then parses that SMT into its dedicated
Z3 context. No private backend or Rust pointers are used. Named symbols and
sort declarations come from the public export. Cached translations reuse Z3
expressions. Serialized SMT may expand sharing; this prototype does not claim
linear serialization cost or preserved internal AST shape.

Linux supported check: nix develop --no-write-lock-file --command
scripts/bazelw build --config=reapi //extractor:corpus_native_models.
No candidate native execution. Real O0/O2 alias/overlap/division extraction.

Final frozen candidate on Hotei: /tmp/wruh-angr10-smoke2; service wruh-angr10-final.
Logs and fixed baseline/candidate models are preserved in models-and-logs.tar.gz.
Resource envelope: 8 GiB, no swap, 4 CPUs. Initial Nix bootstrap used
max-jobs 2 / cores 2; final run reused that built environment.
The final Bazel extraction build passed (24.283s, 29 actions).
All six models report PASS. ELF hashes, CFGs, edge counts and occurrence counts
match baseline. Expression syntax differs (including tautology elimination and
zero-extension normalization). All 196 edge checks are UNSAT: guards, all simultaneous state updates,
mirrored PC, and symbolic targets. Twelve public SMT-boundary controls pass,
including Boolean literals, symbols, arithmetic, division/remainder, shifts,
extract/extend, ITE and comparison; cache identity is checked too.

The initial Boolean-literal smoke exposed result-equality simplification;
public BoolV translation fixed it, and all final checks were rerun.

Limitations: only these six models and twelve controls are exercised; no new
native SUT execution, broader architecture coverage, controlled performance
comparison, or Darwin/aarch64-Linux runtime validation. Those platforms have
pinned release-wheel sources only. Angr emits an optional Unicorn-load warning;
WRUH already disables Unicorn and uses VEX. That feature is not validated.
