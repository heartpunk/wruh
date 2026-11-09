# Fix 1: requested memory values and installation write allowance

Base 6bb0359411ab4b1a599058b71b30367c335f7cdc.
Bootstrap SHA256 b84374b115295f5978c49db1a667a57205b06fc878b9093dd9b1147755805ebe.
movProfile now takes the fixed requested-memory address list and includes the
values at those addresses in its requested input views. The ambient-memory
boundary equality is removed. Its installation frame and preparation footprint
allow requested addresses plus existing input slots. Other bytes remain framed.
This changes requirements, not the existing loader implementation. Scratch
collision, requested-PC support, capture and other audit findings are unchanged.

NixOS Lean4.34.0 checked Bootstrap and dependent MovInstaller sequentially;
exit0, no diagnostics, retained loader axiom report only standard Lean axioms.
AYXG324752afe80b05d7fd8854834725cf5ee360f173. Git metadata preserved remotely.
Unit observer-fix1, invocation4f8c9c621ce04b2abf83ef526c1f3ff1,
fleet-build.slice,2GiB/no swap/one CPU/TasksMax64. See logs and resources.
