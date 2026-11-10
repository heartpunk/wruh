# Sparse input memory contract

Base: ff4328fa821dc5f7ae1091c8e9b981e597a1a370.
WholeObserver.Request now uses InputState with a SparseMemoryImage: a finite
list of byte arrays with explicit half-open endpoints, exact length and bounds,
and pairwise nonoverlap. Endpoints are Nat to permit an exclusive end of 2^64.
There is no workload-size cap or operand-derived address restriction.
The byteWrites projection reuses the existing byte-addressed installation and
frame vocabulary. Every supplied byte is required by InputInstalled; the whole
image is used by installationWrites and LayoutSeparated. Output selection and
its fixed quotient completeness contract are unchanged. No native implementation
or new proof is added.

NixOS Lean 4.34.0 typechecked NativeBoundary, Bridge, Transfer, VectorProtocol,
LegacyFp, FaultProtocol and WholeObserver, exit 0. Two existing unnecessarySimpa
warnings in VectorProtocol remain. Source hash, AYXG revision, snapshot and
bounded fleet-build execution details are retained alongside this note.
