# Approved native differential run

Baseline: `c2eae4715c1e` on `corpus-zeroth`.
Runner/model extraction: `7f4815f45eda8d725618657739ff0e48213a61ad`.
Campaign/launcher: `9ff7c9aab71d413292030851ac849dddefe7f5e5`.
User explicitly approved the rest of this goal, including exact audited
candidate native execution, after receiving the scope description.
The earlier `AUDIT.md` records the pre-approval state.

Binary SHA256 values and runtime mounts are enforced by `sandbox.py`.
Only five decimal uint32 inputs; case 0..2 and offsets 0..7. Exactly the
previously audited O0/O2 binaries. Read-only glibc closure (four store paths)
and candidate; fresh namespaces, no network, zero capabilities,
no-new-privileges, cleared environment, disposable 1 MiB /tmp. Per invocation:
256 MiB memory, no swap, one CPU, 64 tasks, two-second service lifetime.
Five-second observer timeout is an INCOMPLETE disposition, not a match.

Trusted Python isolation probe verifies user/net/PID/mount namespaces differ
from host, only loopback exists, effective capabilities are zero,
no-new-privileges is set, home/workspaces absent, runtime read-only, and /tmp
writable. Trusted probe additionally mounts its Python closure; candidates
receive only the four-path libc closure. No security claim beyond these
measured boundaries; no hostile-binary fuzzing.

Supported invocation on frozen NixOS snapshot:

```
WRUH_GHOT_ROOT=/tmp/ghot-handler-equiv-4097a20e nix develop --command scripts/bazelw run --config=reapi //extractor:native_differential -- --output=/tmp/wruh-differential-9ff7c9aa.json
```

Detached frontend unit: `wruh-differential-9ff7c9aa.service`; 8 GiB memory,
1 GiB swap, two CPUs (0,1), 4096 tasks. This build-capable frontend allocation
coexists with the recorded 40 GiB tmux reservation on the 92 GiB NixOS VM;
logical CPUs 16 and 17 remain available for administration. Each native
invocation uses its own stricter cgroup. Compilation/extraction actions use
the configured REAPI profile.

STS execution uses AYXG's evaluator, one old valuation per simultaneous
update. SysV function entry has rsp mod 16 = 8, fixed private stack and
32-byte storage, explicit return sentinel, zero default memory/initial flags.
The three admitted functions don't depend on uninitialized input registers,
flags or memory. Return values and all storage bytes are compared. Stack
addresses differ from native; the functions don't expose those addresses.
Harness main/libc startup are not extracted or compared.

Deterministic inputs: eight integer boundaries; alias equal/distinct endpoint
pointers; overlap offsets 0/1/7; division denominators 0/1/3/UINT32_MAX.
Hypothesis: 64 generated examples per function per optimization level,
seed 20261002 + function index, no database, shrinking retained on failure.
Any ambiguous/stuck/fault/step-limit or native execution failure is INCOMPLETE;
any differing return or storage byte is MISMATCH, preserving its input.
