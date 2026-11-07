# Fixed loader PC validation

Checked source: `ed225bafd5fd73020bba3d83a13a3a6d8097ef31`.

`protocol_loaded_pc` proves that the modeled loader leaves RIP at 4194672
(0x400170). `protocol_sound` includes this conjunct. This does not establish
native execution or arbitrary requested RIP installation.

## Typecheck

NixOS unit `wruh-protocol-pc-20261107.service` exited successfully (0).
Lean executable: `/nix/store/qpk7v7b4ixkpa4jfsvgmmsmdr4l23in1-lean/bin/lean`.
The committed snapshot includes Git metadata. It reuses the same matching
Pipeline/Proof/InputModel/Extracted compiled dependencies documented in
`../protocol-input-memory-frame/README.md`. `Protocol.lean` itself was checked
from the new snapshot. Exact command and resource measurements: `service.txt`.
All printed declarations use only propext, Classical.choice and Quot.sound;
no sorryAx. Full output: `typecheck.log`.

## Astra light source review

Reviewer: /root/review_loaded_pc, gpt-6-astra, low reasoning.
Verdict: pass, no blockers. Read-only; reviewer did not run builds.

The theorem derives RIP 4194672 from run.inputStep.2 and reduces the existing
loader update by reflexivity. It adds no desired-result hypothesis or
replacement model. protocol_sound includes precisely that fixed-PC property
while retaining the other conjuncts. Neither arbitrary requested RIP
installation nor native execution correctness nor Linux ptrace refinement is
claimed. ProtocolExecution bounds the claim to the modeled protocol.

Reviewed declarations: Protocol.lean lines 11–25, 51–84;
models/InputModel.lean lines 23–24 and 115–116 at the checked source revision.
