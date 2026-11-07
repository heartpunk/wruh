# Checked addition: protocol input-memory frame

One added theorem: `MovObserver.protocol_input_memory_frame` in the existing
`Protocol.lean`. The existing `protocol_sound` now includes that conclusion.
For every address outside `inputWrites`, memory at the original target's entry
equals ambient memory before private-slot preparation and loader execution.
The proof reuses `writes_frame` and `loader_preserves_mem`.

- Checked source: `ca47f9175315c657688f4c67f37e4f367bd59a45`.
- Result: Lean exit 0; both the new theorem and upgraded `protocol_sound` report
  only `propext`, `Classical.choice`, and `Quot.sound`; no `sorryAx`.
- Lean 4.34.0, compiler `293d5d0c0c3f3dded4688b3ccd6a33939ac5102b`.
- Host: NixOS; unit `wruh-protocol-input-frame-20261107-r3.service`.
- Bounded child of `fleet-build.slice`: 2 GiB memory, no swap, one CPU,
  one Lean thread, 128 tasks, 180-second runtime cap.
- Wall interval: 2026-11-07 13:31:52–13:32:10 America/Los_Angeles.
- Peak memory: 876986368 bytes; CPU time: 14168585000 ns.
- Full output and actual launch command/resources: `protocol-input-frame-r3.log`
  and `service-r3.txt`.

Source authoring and commits were local under `~/workspaces/wruh-mov-observer`.
The remote execution snapshot included Git metadata and had the checked commit
as its detached HEAD. The pinned Nix development shell supplied Lean. The
existing AYXG Lake environment and compiled observer dependencies were reused;
the following cached dependency sources matched the local source byte for byte:

| Source | SHA-256 |
|---|---|
| Pipeline.lean | `3d8a33e6923a69eaadd366646430069d0d12eb342e59bef1f8d5c6445396cdad` |
| Proof.lean | `ca028b8e7f5483705b467a31b62723427c1895138ed5b4bcd785c542f767acaf` |
| InputModel.lean | `b47b0a2b07d54a3e0058294aec884f383d95b9a871685e02d4b7368cafa8e590` |
| Extracted.lean | `8798b7f6bab466c02698640bc736701caa26dd55332346614ac8f48de13f2058` |

Attempt 1 stopped before theorem checking because Lean's working root did not
contain the input source. Attempt 2 found a rewrite elaboration issue; the
source correction exposes the concrete `loadUpdate` before using its existing
memory lemma. Both unsuccessful logs are retained alongside the successful run.

Scope: the existing extracted-model protocol. This closes its input-memory
frame clause, not the future native ABI/stop/fault proof. No new runner, native
experiment, additional theorem, or full end-to-end completion is claimed.
