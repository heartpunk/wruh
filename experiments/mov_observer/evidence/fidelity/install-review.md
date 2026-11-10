# Executable GPR installation fidelity

The actual observer calls InstallationEncoding.encodeGprs and all four executables
link that module. InstallationFidelity proves every byte/word of the resulting
128-byte record, concrete decoding, enabled execution at the actual loader entry,
and equality to all caller GPRs under the unchanged architectural size16 check.
Arbitrary ambient memory/register values are allowed. No preinstalled-state
premise, admission restriction or new quotient is introduced. Existing sparse
memory installation proofs and the runtime sparse write loop are unchanged.

Parent, capture-lane cross-review and independent reviewer approved. Cross-review
required explicit entry-PC/guard linkage, which is now proved. A new native BV
reflection axiom was caught by the axiom audit and removed via algebraic rewriting
and reuse of the existing byte_roundtrip theorem. Final typecheck passed with only
propext, Classical.choice and Quot.sound throughout the new theorem chain.

The updated executable passed all29 observations plus loader rejection on the
existing AVX512 KVM guest, using the same signed flake environment and NixOS build.
Kernel/FFI writes, full FP/vector conversion and whole-observer correctness remain
outside these component theorems; no such claims are inferred from this result.
