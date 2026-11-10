# Astra Max review — flags buffer

Single substantive review: PASS; no blocking findings. Source-only, read-only; no delegated reviews or independent builds.

Base: b76f1a312ecca259c7fc624ac4d9b19aa8b92227.
Proof SHA-256: d59ed8714111a7a124123daa64f0ef646730bbc21b306a86630dbbabaf2ebb04.
Shared runtime SHA-256: cc653f143838698954537cba575857a34f8d4e9c4938f58f0960459b1fcd53e9.

FlagsBuffer.lean preserves word/putWord verbatim and uses the original 18*8 flags offset. Observer.lean calls these helpers for installation, installation readback and terminal read. The native build compiles and links the shared module into all four executables.

FlagsBufferFidelity proves length preservation, every byte outside [144,152), every written byte, all UInt64 read/write roundtrips for buffers of length at least152, and modeled-flags recovery plus unmodeled-bit preservation via the existing flags_conversion_correct. No converter, domain or quotient change, added axiom, sorry, native_decide/bv_decide, preinstalled-value premise or hidden-write assumption. Protocol and FlagsConversion are unchanged.

Matching NixOS evidence reports exit0, standard propext/Classical.choice/Quot.sound dependencies, all four executables built and12 scalar observations passed. The reviewer inspected this evidence but did not independently execute it.

Scope is the pure flags-buffer operation, not the surrounding RIP/orig_rax writes, kernel SETREGS or whole observer. Runtime Request continues carrying the raw UInt64 word; it is not claimed to invoke the modeled codec.
