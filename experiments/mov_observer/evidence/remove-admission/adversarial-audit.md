# Independent adversarial audit, 2026-11-09

Status: admission escape removed; full installer and observer acceptance remain
INCOMPLETE. This is a synthesis of two independent fresh Astra Max source-only
reviews, plus the original Astra's re-review. Neither fresh reviewer ran builds
or edited sources. Findings are source-derived counterexamples, not newly
machine-checked counterexample theorems.

Reviewed baseline: a2126801b431358d4cce746bb80b02518b6b0b62.
Immediate withdrawal reviewed: 2adf40f32915734033491e98e2e1a3a5251bd206.
All paths below are relative to experiments/mov_observer at the baseline unless
explicitly labeled withdrawal. The governing initial scope remains user-fixed
GPRs plus operand-memory ranges, later FP/vector extensions; this audit does
not silently require all architectural features immediately.

## Findings agreed by both fresh reviewers

1. Requested memory was assumed installed. MovInstaller.movInstallerProfile
   required wanted/ambient equality; mov_installation_coverage used admitted.2.
   Witness: requested operand byte 0x600000=0x7a, ambient=0x11, valid fixture PC.
   Preparation and loader leave 0x11. Withdrawal correctly removes the gate and
   certificate. The remaining movProfile boundary equality AND movInstallProtected
   frame still require ambient outside-slot bytes; both need actual requested
   writes. WholeObserver.InputInstalled and installationWrites already distinguish
   requested memory, instruction bytes and private preparation from surroundings.

2. Scratch cannot erase requested operand memory. MovInstaller.movInputQuotient
   excludes the fixed input slots without establishing semantic privacy. Witness:
   requested operand bytes at 0x601140 are zero, requested RAX=1. Preparation
   overwrites the requested operand with 1, which that quotient does not see.
   Required operand ranges must take precedence: place scratch elsewhere or
   restore requested contents. LayoutSeparated must be discharged, not used to
   drop ordinary requests. A construction-chosen quotient is not user-fixed scope.

3. BootstrapObligation lacks inputQ/InstallationCoverage. AccessToBootstrap
   concludes a weaker goal and drops explicit input adequacy. Faithfully observing
   execution from wrong input does not repair installation. The final required
   goal must retain the user-fixed input equivalence at actual target entry.

4. WholeObserver.ObserverCoreContract omits CaptureAvailable. One terminal state,
   no steps, empty history, setupFailed invalidState, empty footprints satisfies
   it even for coherent requests. Success/legitimate target outcomes must be
   required under fixed ordinary operating conditions. Do not blindly conjoin
   current CaptureAvailable: it only accepts captured.observed, while actual
   target exit is also a legitimate modeled outcome. No new implementation-owned
   availability filter may replace admission.

5. Output coverage and frame authority are unbound. WholeObserver.Request selects
   outputFields/outputMemory, FaultProtocol.ResultFaithful checks only those.
   Empty output lists can satisfy accuracy and even successful-capture availability.
   The whole-observer requirement must bind output selection to the fixed quotient.
   LayoutSeparated omits output-only and other target-visible bytes unless supplied
   protectedAddress includes them; this must not be construction-selected permission
   to overwrite state. Accurate saved output alone is not preservation.

6. Pure/ghost execution is not concrete binding. Construction.prepare/handoff can
   mathematically do all work while the basis is empty; CaptureState.saved can
   mathematically contain original state without actual saved storage. WholeObserver
   executions, histories, receipts and returns must bind to the same real operations,
   actual saves and bytes. Existing comments acknowledge this gap; comments cannot
   satisfy it. No new runtime logging/effects language/OS proof is implied.

7. Duplicate output requests are rejected unnecessarily. RequestCoherent demands
   output lists Nodup and the fidelity contract forces invalidState otherwise.
   Duplicate identical outputs are satisfiable; uniqueness needs explicit user
   canonicalization policy or removal. Contradictory INPUT assignments are distinct
   and genuinely unsatisfiable.

## Additional findings

Fresh reviewer B: Ordered permits transport in every phase. One targetStart,
TWO successful singleStep/wait pairs, then targetStop at the second receipt can
satisfy the history predicates. Bind the target phase to exactly one target
resumption and its original stop/exit before any further resume. Complete logs
alone do not reject this witness. References: WholeObserver.Ordered,
TargetStopReceipt, TraceConsistent; Bridge.OperationReplyCompatible.

Fresh reviewer A: failure causality remains incomplete. TransportFailureSupported
returns True for invalidState/missingState/captureFault/interrupted branches;
failed capture fidelity retains stop evidence but does not justify the reason.
Bind failures to actual conditions and USER-approved retry/abort policy; target
faults must remain outcomes and target replay must not be silently introduced.

## Necessary conditions versus escape predicates

Both reviewers: keep AccessSpec.enabled and intermediate assertions. AccessSequence
must establish them from each required pre-state; AccessCorrect requires successor
existence and every successor's correctness. Singleton start states are inhabited.
These do not independently allow skipping requested installation.

Fixed model/quotient and real representation consistency can be legitimate;
implementation-selected scope is not. Flags ModeledFlags.Valid describes actual
encodings (d=+/-1, ac/id bits). Invalid modeled encodings must be explicit, not
silently discarded. Fresh reviewer B distinguishes requested representability
from ambient validity: native acquisition should establish the latter, or a
pure arbitrary-environment installation proof must not assume it away.

Mapping/buffer/progress conditions need concrete justification. Preparing valid
mappings is generally harness work, not permission to refuse ordinary values.
The fixed fixture PC is an implementation/layout choice, not universal necessity.

## Review failure and present status

The previous source review visibly accepted the preinstalled-memory restriction.
It checked consistency of a narrowed theorem instead of rejecting the task
substitution. The original reviewer now explicitly acknowledges that failure.
The two fresh reviewers independently concur. The historical positive review is
withdrawn as evidence of fulfilling the requested installer.

The immediate withdrawal fixes one acceptance escape only. Generic composition
results are still Props, not proved generic theorems. The retained
mov_loader_access_correct concerns the exact extracted register loader, not a
completed installer or native observer. Broader repairs above are open, not
silently implemented or certified by this audit.
