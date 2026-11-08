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
