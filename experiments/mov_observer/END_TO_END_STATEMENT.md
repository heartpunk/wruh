# `observer_end_to_end_correct`

**Work-in-progress statement. Not yet a closed Lean declaration or a proved
theorem. This file is the first persisted checkpoint of the replacement for
the abstract goal schema.**

## Purpose

For one instruction, obtain native evidence that can expose incorrect or
incomplete Wruh/AYXG semantics. The observer must not manufacture agreement by
changing the target execution, losing state, consulting a predicted answer, or
classifying its own implementation defects as unsupported target semantics.
State belongs to the common Wruh/AYXG architectural representation. Raw native
buffers are retained as evidence; they do not define a competing state model.

## Objects the statement concerns

`A` is the actual implementation artifact: the selected Lean entry point,
concrete foreign bridge, exact installation/capture/fallback instruction bytes,
and the linked executable produced from those inputs by the pinned build.

`q = (instructionBytes, initialState, mappings, platformContext)` is one requested
instruction execution. `initialState` uses the common Wruh/AYXG representation;
the mappings include addresses, permissions and bytes. The platform context
identifies the processor capabilities and relevant execution configuration.

`r` is a complete execution of that executable on `q`, including supervisor,
bridge, kernel interactions and tracee instructions. Its events are facts in the
execution semantics, not assertions emitted by the observer's logging code.

`b` is an execution of the original single instruction from the same requested
state and relevant external choices, without the observer's execution effects.
Its outcome contains retirement or the original exception, architectural partial
effects, post-state and relevant exception metadata. It is native/reference
execution, not the predicted Wruh/AYXG result under test.

## The required conclusion

For every request in the fixed required profile, assuming the named external
ISA/kernel/compiler/runtime contracts and termination of the target instruction:

1. **The executable is the implementation being proved.** Its image equals the
   pinned compilation/linking result for `A`'s actual Lean source, concrete bridge
   and exact stubs. All foreign symbol bindings, calling conventions and layouts
   used in the proof are those of that image. There is no premise asserting that
   our bridge, marshalling, codecs or supervisor already behave correctly.

2. **Every maximal execution returns.** Every maximal `r` is finite and ends in
   a classified return. A finite stuck execution, unhandled abort or infinite
   execution violates this conclusion. The progress premises concern the target
   and named external primitives, not the correctness or termination of our code.

3. **A successful return is about exactly one original target invocation.**
   There exists exactly one target invocation in `r`. Its fetched bytes equal
   `q.instructionBytes`; its actual entry state and memory equal the requested
   effective initial state. Its processor/context identity is the requested one.
   Target instructions inside a branch destination are not executed as additional
   test instructions. Architectural partial progress of the same instruction is
   retained, including on an exception.

4. **Instrumentation preserves that execution.** For that invocation there is
   a corresponding `b` with the same relevant external choices. Their target
   events, architectural effects and post-states are equal. Debug flags, stopping
   mechanisms, redirection and observer memory must not change what the target
   computes. Capturing a perturbed execution perfectly does not satisfy this.

5. **The returned evidence equals that outcome.** For every architectural field
   required by the fixed profile, the returned value equals the actual value at
   the original target boundary. For every requested mapped byte, the returned
   value equals the corresponding byte at that boundary. The reported event,
   stopped PC and exception metadata equal the original event's values. Original
   raw capture bytes are retained. Any representation conversion must preserve
   the distinctions required by those equalities.

6. **Observer effects are accounted for at every prefix.** Observer writes stay
   within their declared owned regions. Outside those regions, each observer step
   preserves memory and permissions. Before overwriting a target field needed by
   the observation, its original value must already be present in a designated,
   still-valid saved location. Later capture and fallback use that saved value.
   These conditions apply to interrupted prefixes as well as completed fragments.
   Cleanup releases the child and temporary resources, transferring only the
   returned evidence's ownership to the caller.

7. **Failure reports describe actual acquisition failures.** A failed return
   identifies an actual failing operation/event in `r`, with its actual arguments,
   error and phase. The target has been invoked at most once. A fallback observes
   that same invocation; it does not rerun it. A target exception is an outcome
   to capture, not sufficient grounds to call capture unsuccessful. An
   implementation defect remains an implementation defect even when detected and
   reported accurately.

8. **Successful capture is required where the agreed facilities suffice.** Under
   the separately specified environmental availability conditions, every maximal
   execution returns a successful observation. Those conditions cannot include
   "our wrapper succeeds", exclude cases discovered to fail, or depend on the
   comparator verdict. Required cases must inhabit the profile. Honest failure
   reporting alone does not satisfy the observer's purpose.

9. **Comparison has the specified mathematical meaning.** For a faithful
   observation `o` and separately evaluated instruction model `M`, acceptance is
   equivalent to membership of the actual observed labeled transition in `M`'s
   permitted transitions, with the agreed treatment of architectural
   undefinedness. The native event correspondence must not invent an observable
   model edge identifier. Missing required state produces an explicit coverage
   failure, never acceptance. Neither native acquisition nor event classification
   takes `M`'s predicted outcome as input.

## Still to close before this statement is review-ready

- Replace the descriptions of profile, effective initial state, relevant external
  choices, availability, regions and saved locations with exact definitions.
- Bind execution, maximality, source-to-image identity and return decoding to the
  concrete semantics used by the Lean proof. Do not substitute unconstrained
  predicates for these definitions.
- Express the complete conclusion as the single Lean proof obligation
  `observer_end_to_end_correct`; implementation and proof may remain unfinished.
- Identify the specific external primitive contracts, including the progress
  contract and debugger effects, rather than assuming an opaque correct observer.

The stopping mechanism and feasibility of extracting the compiled bridge remain
implementation experiments. They may change how the obligation is discharged;
they do not authorize weakening its meaning. Any repair must preserve both the
contract and the purpose above; uncertainty about either returns to the user.
