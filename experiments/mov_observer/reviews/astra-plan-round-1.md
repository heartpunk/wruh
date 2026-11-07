# Astra plan review — round 1

Reviewer: `gpt-6-astra`, reasoning `max`, `/root/observer_plan_review`.
Reviewed plan SHA-256: `6517b3a825006a07a2f64fe221ea42fe73b6f1354c491ee1a537aa8961e519b8`.
Scope: in-process, source-only review; no builds, experiments, writes, or remote work.
The reviewed plan is preserved as `plan-round-1.md` alongside this review.

## Verbatim review

Recommend one focused revision before implementation fan-out. The architecture and three-lane arrangement are sound; the remaining issues concern executable acceptance and dependencies. The existing protocol correctly identifies its handoff as modeled and takes the target transition as a premise—it does not claim a Linux implementation proof.[^protocol]

Reviewed `PLAN.md` with SHA-256 `6517b3a825006a07a2f64fe221ea42fe73b6f1354c491ee1a537aa8961e519b8`. This was source-only review; no builds, experiments, edits, or remote work occurred.

1. **Make capture independence and the comparison theorem explicit.**  
   Lines 78–82 and 97–117 point in the right direction, but still permit an implementation to inherit the prototype’s model-supplied edge/post-state as part of its native observation. In the prototype, those values are deliberately supplied by the modeled execution.[^protocol] The future capture/classification API must not receive predicted outputs or the expected edge.

   Add:

   > Native acquisition and event classification depend only on the request, fixed profile and observed bytes/events; their APIs receive no predicted post-state or expected model edge. Freeze an executable `Required` relation independently of the comparator. Prove comparison correctness conditional on a successful capture, using assumptions about installation, observer fragments and FFI behavior—not an assumption that the target agrees with the model. A native event with no corresponding model outcome remains a mismatch or an explicit model-coverage obligation.

   Also require positive admitted cases and successful captures for each required coverage class. Otherwise rejecting every request or always returning `CaptureFailure` can satisfy soundness conditions vacuously. VTDO explicitly separates accepted-capture correctness from availability.[^availability]

2. **Replace “snapshot target state before a fault-capable observer operation” with a realizable preservation contract.**  
   Lines 109–112 and 135–136 are insufficient together. Remaining in the same tracee after an observer fault does not establish that the original target-stop state remains available: an earlier capture prefix may already have changed it. Requiring a complete snapshot before capture also risks assuming the observation capability being built.

   Replace that sentence with:

   > Freeze the target event, stopped PC and available OS metadata before redirecting execution. For each capture fragment, specify successful and aborted-prefix effects. Preserve every not-yet-observed target field, or establish a saved-value/restoration account before modifying it. A fallback may use only evidence and state proven to correspond to that original target stop; otherwise return `CaptureFailure`. Missing native exception semantics remain explicit calibrated assumptions or unresolved obligations.

   Full-fragment frame proofs alone do not establish this property. The current capture specification describes completed execution over total modeled memory.[^capture]

3. **Move the minimum representability audit into C, before freezing the common contract.**  
   C currently freezes the profile before P performs its representability audit. That can force a shared redesign after branching. The existing context includes `sseround`, `fpreg : bv512`, six named arithmetic flags and separate `d/ac/id`; these are not already complete architectural MXCSR, x87 and RFLAGS records.[^state]

   Add a small C-owned field/outcome table:

   > For each required field or outcome, record its raw representation, model representation or named gap, definedness rule, installation method, observation method and owning lane. Explicitly classify target memory, FS/GS/segment context and model bookkeeping fields. Establish the required profile independently of implementation success; unresolved representation or fault-model gaps cannot silently become exclusions.

   This need not repair the models. It must expose where the promised completion is blocked. Assign P and V ownership of their **input installation and any restoration**, as well as capture; those responsibilities are currently implicit.

4. **Show the actual dependency of P/V native calibration.**  
   Lines 46 and 52–53 say F supplies the transport while P/V can calibrate independently. That is achievable, but the independent execution path has not been named. The existing Python probe is a calibration-only GPR capture runner, not the proposed general transport.[^probe]

   Change the DAG/table to choose one explicit arrangement:

   > C freezes the transport signature and synthetic event fixtures. P/V native calibration uses a named calibration-only runner available at C; F independently implements the production Lean/FFI transport.

   Or, if that runner will not exist:

   > P/V proofs start after C; their native calibration waits for F’s concrete transport milestone.

   Add coordinator ownership of the shared emitters, generated context/layout, build wrappers and final composition files. Directory ownership alone does not settle those shared files. Neither arrangement needs a continuously integrating worker.

5. **Add a short calibration table showing what each assertion knows.**  
   “Where independently knowable” in lines 151–154 leaves the critical division to each worker. A compact table would make delegation much safer:

   | Stage | Independently available evidence | Assertion |
   |---|---|---|
   | Installation | Generated request and actual read-back before target execution | Requested state was installed; discrepancies stop the case before target execution |
   | Capture-only calibration | Known seeded state and a separately identified native observation route | Capture preserves/records the seed and obeys its frame contract |
   | Event classification | Synthetic transcripts, then native fixtures with independently established outcomes | Correct event category, PC treatment and partial-effect handling |
   | Arbitrary-target comparison | Validated input, captured raw event/state, separately evaluated model | Agreement under `Required`; the model prediction is the subject of the test |

   Record shared calibration dependencies honestly: two paths using the same kernel ABI are useful cross-checks, not independent proofs of that ABI. Deliberate corruption should cover wrong event classification and missing fields as well as wrong payload bytes.

Two useful, nonblocking plan improvements:

- Add the first execution gate, **after authorization**: re-establish the existing Lean and native capture baseline from the promoted paths at `50ab63f138a5f9a6d7e34ad281a98b5b5e124887`. Preserve the distinction between unchanged checked source hashes and wrappers that have not yet been rerun natively.
- Make minimization reviewable with a small manifest of exact instruction forms used for installation, capture, restoration and fallback, including side effects and model support. Require a reasoned choice; do not introduce a global optimality proof.

The plan is not too large for delegation. These additions can replace some repeated prose about frozen contracts and raw evidence. I would keep the eight obligations, lane table and handoff requirements; no extra lanes or broader model-repair project are needed.

[^protocol]: `wruh` at `385891242c60389e8548428f8022079eb85e9c7d`, `experiments/mov_observer/Protocol.lean`, `ProtocolExecution`, `ProtocolExecution.observation` and `protocol_sound` (lines 11–43); `Pipeline.lean`, `Observation` and `captureObservation` (lines 1448–1464).
[^availability]: `vtdo` at `680c89b6b6960b6b67b701908a23a14c72faa463`, `Convergence/ObserverSketch.lean`, `BoundedCaptureLaws` (lines 69–77), `accepted_check_iff` (lines 155–166), and availability discussion (lines 184–191).
[^capture]: `wruh` at `385891242c60389e8548428f8022079eb85e9c7d`, `experiments/mov_observer/Proof.lean`, `CaptureSpec` and `modeled_step_captures` (lines 76–102); `Protocol.lean`, modeled completeness boundary (lines 53–55).
[^state]: `wruh` at `385891242c60389e8548428f8022079eb85e9c7d`, `experiments/mov_observer/models/Extracted.lean`, `Γ` (lines 8–98).
[^probe]: `wruh` at `385891242c60389e8548428f8022079eb85e9c7d`, `experiments/mov_observer/native_probe.py`, `snapshot` (lines 67–134) and `property_test` (lines 164–186).
