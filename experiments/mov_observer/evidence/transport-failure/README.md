# Transport-failure evidence checkpoint

Source: d8efc3e029680a2d39e6fb1b73df8be9119e2440.
Protocol, NativeBoundary, Bridge, FaultProtocol and WholeObserver typechecked on
NixOS, Lean 4.34.0, with unchanged pinned dependencies. Exit 0; resources attached.

Terra 6.1 targeted review passed: matching errno evidence belongs to the same
process and phase; created-but-not-ready process failures are expressible;
setup error support must match the terminal setup phase. This does not prove
that the matching earlier error caused the return, nor stop-token freshness.
Those remain distinct obligations. Other failure categories also remain open.
