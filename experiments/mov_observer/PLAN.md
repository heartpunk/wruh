# Observer completion plan

## Governing telos and scope — agreed 2026-11-08

This agreement governs the work. Keep it in VCS when removing it from the
working tree later. Cleanup is authorized; implementation awaits approval of
the bounded implementation goal.

The purpose is a minimal, trustworthy native observer that unblocks regression
PBT for existing semantic coverage, not a general verification framework.

### In scope

- Ensure noninterference of native instruction observations: install requested
  state, observe the single target instruction, and capture its result without
  the harness corrupting the observation.
- Treat target-instruction faults as observed outcomes, distinct from harness
  failures.
- Ensure nonexceptional harness runs complete. Trivial transient exceptions may
  be retried where safe; other failures abort the run. Never silently replay the
  target. An aborted run must remain visibly aborted, not become a passing
  comparison. Truly exceptional substrate failures may crash; there is no
  requirement to build recovery machinery for them.
- The user is ALWAYS in the loop on retry/abort decisions. Do not independently
  choose which failures count as transient, whether retry is safe, retry bounds,
  or which cases abort. Propose concrete behavior and resolve it with the user
  before encoding that policy.
- State the concrete obligations needed for these properties using the existing
  instruction semantics and the documented ABI. First check whether suitable
  Lean representations of the ABI already exist, preferably in the distribution;
  reuse them when adequate. Do not presume they exist or invent another framework
  before checking. If absent, state the needed documented ABI properties in Lean
  as a minimal contract stub to which our concrete functions can be bound.
  Distinguish imported ABI contracts from obligations on our own handoff code.
- Use ordinary Lean and a concrete ABI handoff. Do not introduce an effect
  language/interpreter or re-prove the runtime, OS, allocator or ABI itself.
- Extend the AYXG-facing FP representation losslessly as already authorized;
  do not silently narrow coverage to avoid the representation gap.

### Out of scope

- Validating imagined hostile or inexplicable changes underneath the controlled
  harness execution; no concurrent-environment modeling project.
- Paranoia-driven checks, generic ownership/reference-rights frameworks,
  effect languages, or exceptional-failure recovery infrastructure.
- Anything beyond the bare minimum needed to support the regression PBT loop.
  Do not expand the scope to make the specification appear comprehensive.
- AYXG/native semantic comparisons in this observer-specification work. The
  observer serves that later PBT loop; its current task is faithful,
  noninterfering observation.

### User's governing engineering criterion (verbatim)

> anything more than the absolute most bare bones minimal thing required to support the PBT loop for ensuring we're not regressing on existing semantic coverage
> - to that end, if there is any reasonable chance that any pragmatic engineer in the world of any ilk might w/o self owning and destroying their own credibility or correctness might skip a particular check and get away with it, then we should probably fuckin skip it
> - we are not making a throne to the verification and paranoia god
> - we are trying to actually help real humans in this century accomplish real tasks
> - preferably the very first few *in this calendar year*
> - definitely within the next one

Operational test for each proposed addition: what plausible error in our harness
could make the regression PBT misleading, and what is the cheapest adequate way
to prevent it? If that cannot be answered concretely, or normal competent
engineering would reasonably omit it, skip it. This operational test supplements,
not replaces, the user's criterion above.

## Current work and remaining obligations

Reuse Protocol.lean and its approved framing/fidelity obligations. Keep the exact
stub fixtures, extraction provenance, register/memory mappings, FP/vector layouts,
and original-fault/no-replay constraints. Typechecking is not a correctness proof.

1. Establish a small ordinary-Lean observation path and concrete ABI calls before
   specifying more possible implementations. Check existing Lean ABI definitions;
   reuse them or state only the documented properties our actual calls need.
2. Bind exact installation, capture, return decoding and project-owned buffer
   handling to that implementation. Complete the remaining lossless FP/vector
   state and fault-handling obligations without narrowing the intended coverage.
3. Compose observer fidelity, prefix noninterference and nonexceptional
   termination for that same execution. No AYXG/native semantic comparison belongs
   to this task. Real implementation/proof gaps remain open until discharged.

Do not introduce a wire dispatcher, generic allocator/reference-rights model,
effect interpreter or exceptional-crash recovery. Retry/abort policy always
requires user involvement. Local repairs must preserve both contract and telos;
bring material uncertainty about either to the user. Commit coherent checkpoints.

The next implementation goal is reviewed separately before execution. No observer
implementation is authorized by this cleanup. The user retains all merge decisions.

## Proposed bounded implementation goal — awaiting user activation

Implement one ordinary-Lean native observation path to settle the real harness
and ABI shape. Reuse the existing exact MOV loader/capture fragments and approved
observer obligations. Success is a working, checked implementation slice with
concrete obligations attached, not a claim that the complete observer is proved
or that the eventual regression campaign is limited to MOV/GPRs.

### 1. Ordinary-Lean entry point and control flow

- Read Protocol.lean, NativeBoundary.lean, Transfer.lean, FaultProtocol.lean,
  WholeObserver.lean and the current native_probe.py/stub.py before designing replacements.
- Add Observer.lean with a finite GPR observation request/result and ordinary IO
  sequencing: create a stopped tracee; prepare code/data and requested state;
  run the fixed loader to its existing fallthrough; single-step the target exactly once;
  freeze its stop and PC; run the fixed capture fragment; read and return the
  record; release the tracee. Keep operational values usable by the existing
  AYXG-facing state relations. Ghost Env values are proof state, not executable
  observations or an independently invented architectural model.
- Name the small direct foreign functions in NativeIO.lean. Initially unimplemented
  foreign declarations may typecheck; do not call them a working program yet.
  No generic dispatch/wire format, effect AST/interpreter or runtime simulator.
- Before encoding retry/abort behavior, bring the user a concrete operation/error
  policy for this path. Do not choose transient classes, replay/retry safety or
  retry limits. Work independently on unaffected code while that answer is pending.

### 2. Concrete ABI and one working call

- Inspect the pinned Lean distribution's FFI headers, examples and available Lean
  declarations, plus the Linux ABI used by native_probe.py. Reuse adequate existing
  declarations. If absent, add only the ABI contract stub needed by these functions.
- Add a minimal native_io.c shim only where needed to call Linux primitives through
  Lean's ABI. Keep orchestration in Lean and capture in the exact machine-code stub.
  Use the documented runtime APIs, not guessed object layouts or a new ownership model.
- First make register readback from the stopped fixture work end to end through
  Lean. Establish the actual argument types, borrowed lifetimes, output allocation,
  errno/partial-result representation and caller-visible return type. Use the
  existing 216-byte register mapping. No new general serialization protocol.
- Identify the precise buffer-access segment and its live input/output/scratch
  storage. Bind the existing frame to that segment, separately relating its
  bytes/status to the actual Lean return value. Do not apply a leaf buffer frame
  across runtime allocation or return-object construction. If it does not fit
  ordinary documented ABI use, propose the smallest correction rather than adding
  machinery solely to satisfy the current relation.
- Add Prop/theorem statements for that actual handoff: arguments reach the intended
  stopped tracee; buffer accesses obey the leaf-call frame/lifetime contract; returned
  bytes/count/status represent that operation. Identify imported runtime/kernel ABI
  contracts separately from obligations on our code. No sorry or new axiom pretending
  our handoff correctness is proved. Proofs may remain open as named Props.

### 3. One vertical path through the existing MOV observer

- Implement the remaining small foreign calls required by step 1. Extend the existing
  test ELF layout to contain the unchanged loader/capture bytes plus a separate target
  slot at LOAD_CODE + len(loader_bytes()) = 0x400170. Preserve capture at 0x400000,
  loader at 0x400100, and their RIP-relative data references. Single-step the sixteen
  loader instructions and stop at 0x400170 before issuing the one target step.
  Record the exact fixture bytes. Do not rewrite the observer in C or Python.
- Run a concrete register MOV target as the plumbing witness, with several deliberately
  distinct GPR inputs. Lean drives installation, one target step, original-stop/PC
  preservation, capture and decoding. Target-instruction semantics are not checked
  against AYXG in this task. No new general instruction generator/PBT campaign.
- Check installed GPRs against the request and the captured GPR record against the
  independently acquired stopped post-target GPRs. Check the existing capture memory
  frame and preservation checks relevant to this path. These exercise observer
  fidelity, not a model prediction of the target result. Include one corrupted-record
  check so the validation can actually reject a bad observation.
- Map the implemented entry point and native functions to the retained obligations
  in Protocol/Bridge/Transfer/WholeObserver. Add concrete statements for missing links;
  leave unproved links explicitly open rather than adding arbitrary correctness premises.
  Ghost histories need not become a production logging subsystem. Do not claim a
  typecheck or a smoke run proves e2e fidelity/noninterference.

### Execution discipline and stop condition

- Source of truth: local ~/workspaces/wruh-mov-observer. Use the adjacent persisted
  AYXG workspace only if needed; no speculative AYXG changes. Work locally, build/run
  remotely on NixOS in the existing bounded fleet-build reservation. Keep Git identity
  and caches in remote snapshots; no remote source edits. Use the existing containment
  setup for native execution; do not silently drop it or use bare Entrapta/emulation.
- Typecheck the remaining cleanup first. Then commit early at each coherent checking
  checkpoint. Show the user the concrete signatures/control flow before extending
  the native shim across the complete path. Explain any implementation change that
  might alter contract or telos and obtain their judgment before proceeding.
- Do not implement full FP/vector capture, fault-friendly fallback, batching, performance
  work, semantic fixes or AYXG/native comparisons. Their retained obligations remain;
  this slice neither completes them nor changes the intended final coverage.
- No general Lean runtime/allocator/OS proof. Nonexceptional observer runs must terminate
  assuming terminating target/native primitives under the agreed environment. Truly
  exceptional substrate failure may abort/crash. Never silently replay the target or
  report an aborted observation as success. Failure-policy decisions remain with user.
- Stop after the ordinary-Lean vertical path runs, relevant Lean statements typecheck,
  targeted checks pass, and self-review identifies the remaining proof links. Report
  commits, exact commands/results and the remaining obligations for human review.
  Mark this bounded goal complete only on that basis; otherwise report the concrete
  blocker. Do not continue into broader implementation, publish/push or merge.
