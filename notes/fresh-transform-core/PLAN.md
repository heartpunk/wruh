# Corrected continuation plan

Status 2026-10-03. Discussion plan, not authorization for subsequent implementation.

1. DONE — local transformer helpers/proofs, typed ordered reads, byte memory. Recorded goal work ~35m; first-to-last commit timestamps 09:45:41–10:14:09 Pacific (~28m28s).
2. DONE — AYXG Voogd stepping and source-STS soundness/completeness. Recorded goal work ~10m; commits 13:08:24–13:14:04 (~5m40s). Bookmark `voogd-symbolic-step`, head `179342d8a0b6`, pushed for user's external review. Internal review and Linux checks pass; external review outcome remains pending.
3. DONE — clean WRUH transformer core. Parent `e49b212f14bd`, before obsolete collector/design notes. First retained-core commit 13:28:16; final evidence commit timestamp in JJ. Local proof code retained unchanged modulo imports/comments. No collector or obsolete plan in continuation ancestry. Bookmark `fresh-transform-core`.
4. DONE — universal fresh semantic transport and AYXG instance. Implementation commits 13:44:29–13:54:28 (~9m59s); successful final Linux check 13:54:48–13:54:59 Pacific (11.358s wall, 439M peak), followed by evidence recording. Goal started about 13:41; ~15–20m through evidence. Exact checked revision 4142bd2d7cc5; see notes/fresh-semantic-transport/RESULTS.md. Both directions of source-transition equality and identity bisimulation checked; all AYXG adapter laws discharged. Dense complete-state transformers; sparse diff and production correspondence not claimed. Independent read-only Sol review passed.
5. NEXT — match production fresh.py and called helpers: tentative 20–40m. Explicitly account for source coverage, selector splitting, memory observation timing, terminal/fault behavior, and actual primitive boundary. No VEX structure walker. Escalate substantive mismatch rather than weaken the target. This is operational correspondence work, not a claim to have formally verified Python itself.
6. FOLLOW — production lean.py/angr hookup: tentative 30–60m. Lean performs proved algorithm, Python operates angr; inverted control is allowed. Preserve shared DAG exchange. Lean CLI entry: an additional 5–10m.
7. FOLLOW — existing-model parity through real hookup: tentative 15–25m. Preserve commands/results and distinguish source-semantic proof from production exchange evidence.
8. FOLLOW — initial CPython extraction through the new path: tentative 20–40m for a bounded pilot after hookup. Estimate whole-CPython execution from that pilot, not from these helper proofs.
9. LATER — model CPython/angr and address remaining implementation/ISA-semantic trust. No estimate in this bounded plan.

Times from VCS are spans between commits, not active-work measurements; they omit preceding inspection and may include waits. The recorded goal durations above are separate measurements. Future estimates remain tentative, especially production exchange. Existing selector/host behavior is not silently proved by a generic adapter premise.

The obsolete request-list collector and transcript assembly were discarded from this continuation, not counted as completed universal transport. Their historical bookmarks remain evidence only. Source modifications stay local, new dedicated workspaces/bookmarks for later tranches, fresh only, no automatic push or merge.
