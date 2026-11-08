# Fault-prefix and fallback obligation checkpoint

Source: 3a44f00f387310cda656aa745638dd03a74939ec.
NativeBoundary, Bridge and FaultProtocol typechecked on NixOS, Lean 4.34.0,
with the previously pinned observer dependencies. Exit 0. Resources attached.

Terra 6.1 reviewed and accepted the targeted fixes: memory framed by byte rather
than requiring a saved total array; finite public observations separate from
full ghost model state; successful results require exact required field/address
lists and fidelity for every returned value; whole-array memory excluded;
fallback starts from the last state of an actual failed capture; no target replay.

This is not chunk-3 completion. Still required: fixed native observation profile
and its adequacy, complete actual execution/event binding, stop classification,
failure causality, fault-specific visibility/partial effects, successful fallback
availability where possible, and whole-execution finite completion. No native
observer implementation or correctness proof has been added.
