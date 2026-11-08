# Whole-run obligation checkpoint

Source: 6ca2af72ee822765337c9deaf379f34af54b571c.
NativeBoundary, Bridge, FaultProtocol and WholeObserver typechecked on NixOS,
Lean 4.34.0, with pinned observer dependencies. Exit 0. Resource record attached.

Terra 6.1 reviewed and accepted targeted corrections: ordered same-process
start then stop/exit, capture tied to the same frozen stop, independently coherent
request constraints, exact installed inputs, explicit setup/exit/capture and
post-start unavailable outcomes. Whole-run Acc/progress excludes infinite or
stuck runs once instantiated with the complete actual execution semantics.

This is not the final four-chunk composition. Still required: concrete API/ABI
execution binding; prefix noninterference linked to these same events; true
failure causality; fixed supported profile and coverage; full FP conversion;
external progress assumptions and conditional successful-capture availability.
No observer implementation, proof, or AYXG/native comparison has been added.
