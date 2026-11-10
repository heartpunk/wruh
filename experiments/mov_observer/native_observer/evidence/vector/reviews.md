# Vector checkpoint reviews

Both existing Astra light reviewers reviewed source and final execution evidence.
Technical review confirmed source hashes match build.log, all 25 cases passed,
and retained images comprise 21 xstate images of 2688 bytes and 18 FP images of
512 bytes. Scope review found the practical observer work aligned with the user
request, without proof work or semantic-model comparison. Both passed.

Review corrections applied before execution:
- Capture installed xstate after legacy FP installation.
- Require AVX512BW for KXORQ.
- Include vector-cases.S in source hashes.

Host query: Entrapta QMP /run/qemu-server/104.qmp, query-kvm returned
{"enabled": true, "present": true}. No workload ran on the bare host.

Closure provisioning: Determinate Nix installed using its official installer.
NixOS's existing fleet-builder-vm120-1 public key was added to the guest's
nix.custom.conf. Private key stayed on NixOS. The 91-path approximately 5GiB
nativeObserver closure was signed and copied through a binary cache. Recursive
signature verification passed. The legacy nix-store export route lacked usable
signatures and was abandoned. Direct agent forwarding was initially rejected by
automatic approval review; the user subsequently authorized forwarding within
the homelab, but the completed transfer used the signed-cache route.

Build: NixOS observer-vector-final-build.service, flake nativeObserver shell.
Execution: guest104 observer-vector-native-1.service, same flake shell, binaries
copied from NixOS. Both used bounded child services under fleet-build.slice.
No native FP-to-AYXG conversion or AYXG semantic comparison was added.
