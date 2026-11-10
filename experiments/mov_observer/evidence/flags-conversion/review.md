# Astra Max review — flags conversion

Result: PASS; no blocking findings. Source-only adversarial review against the authorized telos; reviewer did not build or edit.

Reviewed FlagsConversion.lean SHA-256: `bf2ecd0f66fc1bc6407d4a686fccdbfbbce903ccfe249bc117b17d411c95cff5`.
Protocol.lean is unchanged from `80be42ba2bc8a98d26cbc0b6365a8ef6d85a1da7` (SHA-256 `6579ee30b27658185d27557c461e4a538899755e838a133077c9b970bf6494b9`).

The public theorem proves the existing FlagsConversionCorrect exactly, without parameters or additional premises. The proof covers decoded validity, successful encoding with exact field recovery and complement-mask preservation, full original-word roundtrip, and rejection iff invalid. All canonical assignments are covered, including d = +1/all-ones and ac/id = 0/1. No domain or quotient change, alternative converter, sorry, new axiom, native_decide, or bv_decide call.

The pipeline checks the new module immediately after Protocol. This proves the codec obligation only; it does not claim native ptrace installation, architectural layout correctness, or a complete observer proof.

Separate NixOS validation is recorded in typecheck.log and resources.txt. The checked theorem depends only on propext, Classical.choice, and Quot.sound.
