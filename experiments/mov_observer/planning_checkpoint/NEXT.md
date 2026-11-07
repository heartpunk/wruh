# Durable planning checkpoint

Planning only. Do not start observer implementation.

Authoritative source: ~/workspaces/wruh-mov-observer/experiments/mov_observer.
The plan and Lean goal already reside there; temporary paths are staging and remote execution copies.

## Latest user requirement still to incorporate

The end-to-end goal must require NO DIVERGENCE of our observer, conditional on termination of the target instruction and the agreed current/presumed AYXG semantics of the stub plus external contracts. Divergence must not be an accepted outcome or deferred as a timeout/incomplete. This remains a proof obligation, not an implemented observer.

## Current review and validation state

Round 3 at Wruh revision 18bf2e454108438f46f0cfe35e9873e37de6af4e typechecked on NixOS with Lean 4.34.0, compiler 293d5d0c0c3f3dded4688b3ccd6a33939ac5102b. Both logical schema lemmas reported no axioms. Service wruh-observer-goal-20261107-r3b succeeded; native observer tests did not run.

Round 4 incorporates progress composition; authoritative PLAN.md SHA-256 ac9b7b67e7106c1bfbc85c30469b0c794da6dcf8c1e410acfd014c76846d1062; ObserverEndToEndGoal.lean SHA-256 5088cc146bbf980f11200159f6db97a39fdde216718e2a2150004b866898a1ab. Astra max reports no remaining substantive blockers for that revision, but its revised typecheck has not yet run. The latest no-divergence clarification must still be incorporated and reviewed.

Remaining work: preserve remote typecheck logs; get the round-4 final review; strengthen the no-divergence goal; typecheck the final statement on NixOS under a bounded fleet-build child; have Astra review the final correction; preserve reviews and final commit. No pushes, PRs, merges, or implementation lanes authorized.
