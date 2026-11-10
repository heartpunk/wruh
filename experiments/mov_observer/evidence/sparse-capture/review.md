# Sparse capture: single Astra Max review

PASS; no blocking findings within the authorized per-region stage. Read-only review; no reviewer builds, remote access, edits, or delegation.

Base: 2f62f17106e89210a68f06ccf8f96d7eb097c111.
SparseCaptureFidelity.lean SHA-256: 9837deaca419029ae1e188cff739ca298a95423d6efc344b8a18e9375ac4cef2.
Observer.lean SHA-256: 0372711c006af0aa76c7a4c3e73e2082d9a282d8f0962a436a1522a3a8d137e4.

regionRange constructs the existing MemoryRange using the exact address, actual returned bytes, exact size, and unchanged address-space fit bound. regionImage constructs a singleton SparseMemoryImage without weakening nonoverlap. runtime_readback_image_fidelity covers every index of the requested length and uses returned bytes, never assumed input contents. Equal transfer length is explicit; arbitrary finite lengths remain supported.

The actual observeInstruction calls readRequestedMemory after stopping; withReadback consumes each actual readMemory result. Loop order, addresses, sizes, and short-transfer rejection are unchanged. WholeObserver definitions and readMemory are unchanged. The pipeline compiles the actual Observer before this proof. The VectorTrials edit is diagnostic text only and matches the existing feature-bit check.

The current ptrace/OS transfer boundary is accepted as trusted. This proves per-region representation fidelity, not kernel reads, the full collection loop, or aggregate-image construction. No added axiom, sorry, model weakening, prediction, or normalization was found. The reviewed source hash matches the reported successful NixOS check.
