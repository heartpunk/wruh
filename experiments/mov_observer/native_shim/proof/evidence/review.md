# Astra Max adversarial review

Reviewer: /root/shim_telos_review, gpt-6-astra, max reasoning.
Read-only source/evidence review against the user's telos: prove the actual
exact-byte shim's ABI/frame behavior from extracted semantics, without substituting
an ideal model, narrowing away required behavior, or assuming the final conclusion.

Reviewed model SHA256:
a6689376b34d310cabd21d984f849596b8e6b9cfa7c21150b27cf7d446e97b3c
Reviewed proof SHA256:
3569b934b87445bf4a368eb1951ecb895d85f24e3706f59478787fafba867788
Reviewed exporter SHA256:
9e6d2d4de4b9d262e95216dfd3c09b766b9c7196c5e7f1d96ae538024f554db3

Issues resolved before final review:
- Memory belongs in the field clobber list and receives its separate byte frame.
- Preserve size-read ordering and check ordered write events against exported stores.
- Assert exact block boundaries, instruction counts, jump kinds and syscall bytes.
- Establish enabled entry/suffix guards, not only update evaluation.
- Audit all descriptor theorems as well as the overall ABI theorem for added axioms.

Final reviewer verdict:

> No blocking findings for the requested ABI/frame proof.
>
> Reviewed final model a6689376… and proof 3569b934…, checked all recorded source
> hashes, and inspected the successful typecheck and extraction evidence. The
> proof establishes argument/descriptor construction, bounded stack writes,
> borrowed-buffer preservation, raw return preservation, callee-saved state,
> and correct RET behavior.
>
> The kernel assumption remains explicit and noncircular. README correctly
> distinguishes this result from kernel-transfer correctness and full native
> FFI refinement. Validation wiring is correct.

The reviewer requested confirmation of cached imported dependency source hashes;
the parent checked both remote sources against local Extracted.lean and ByteCodec.lean,
with identical hashes recorded in source-sha256.txt. Raw extraction whitespace is
intentionally retained. No kernel or full native-refinement claim was approved.
