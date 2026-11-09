# Fix 3: preserve the fixed input quotient through composition

Base: 3b677e92438e7d3cf4204971b3054d22b70705a5.
ComponentObligations and BootstrapObligation now both require InstallationCoverage
for the same explicit inputQ. The final run conclusion explicitly requires
inputQ.r loaded wanted. CompositionTheorem, AccessToBootstrap and the MOV
specializations pass that same quotient through. These are obligations, not new proofs.

Bootstrap and dependent MovInstaller typechecked sequentially on NixOS with Lean
4.34.0, exit 0. Exact hashes, AYXG revision and bounded fleet-build resources are
in the accompanying logs and script. No other audit fixes are included.
