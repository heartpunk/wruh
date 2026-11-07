# Astra plan review — round 3

Reviewer: `gpt-6-astra`, reasoning `max`, `/root/observer_plan_review`.
Source revision: `18bf2e454108438f46f0cfe35e9873e37de6af4e`.
Scope: source-only review of the end-to-end proof plan and Lean goal schema.
The plan and goal snapshots are preserved alongside this review.

## Verbatim review

**One focused goal revision is needed.** The schema is coherent as a conditional safety theorem, and its coverage/availability conditions exclude an observer with no successful executions. The expanded ABI proof requirement is appropriately explicit.

The substantive gap is **progress composition**. In `ObserverEndToEndGoal.lean`, `nativeToLean` transfers finite executions, while `ComponentProofs.availability` already requires native existence, termination and successful results. `components_suffice` therefore copies native availability rather than deriving it through the proposed executable proof chain.

The coordinator’s proposed repair is sound and small:

- F proves availability for the **actual Lean execution with concrete foreign behavior**.
- The compiler/runtime foundations preserve Lean returns into native executions.
- Existing `nativeToLean` excludes native returned failures when all Lean returns succeed.
- A separate foundation reflects native **nonreturning** executions into Lean nonreturning executions.
- Nonreturning covers every maximal execution producing no `Result`: infinite execution, finite stuck behavior and unhandled abort/exit. Alternatively, abnormal termination may produce a classified failure. No maximal execution may disappear from both categories.

This permits a compositional availability proof while keeping project-owned behavior out of external assumptions.

Two requirements should remain explicit foundation gates:

1. **Concrete ABI proof feasibility.** Before fan-out, demonstrate one representative actual bridge operation—including marshalling and failure handling—in the chosen proof representation, with its source/artifact connection. Merely naming shim extraction as the route is insufficient. This is future foundation work, not authorization to perform it now.
2. **Trust-boundary discipline.** `nativeToLean` remains an arbitrary refinement proposition mathematically; its comment cannot enforce its provenance. Require compiler/runtime laws parameterized by the same concrete foreign semantics on both sides. They must not replace foreign behavior with the desired transport contract. The concrete bridge proof must establish that correspondence.

Availability premises should describe environmental conditions and primitive guarantees, rather than assume that project-owned calls succeed or that the observer never faults. Valid arguments, buffer safety and correct failure handling must follow from the component proofs.

No additional schema-level blocker emerged. At concrete instantiation, independently bind `targetIn`, `targetInvocations` and the frame predicates to the same actual requested target occurrence; do not reconstruct that occurrence from the observation being validated. The plan already provides the appropriate contract-review gate.

Reviewed:

- Plan: `8916c6e3dc0a85bc9f6770f788e49ac52e0fa13e4f126a3b12c8505ab9a34950`
- Goal: `2890533a2232055328a8ba012ce6ccfcbb5e1178517898e48216975db8d1873c`

This was source-only coherence review; I performed no typecheck, build, experiment or edit.
