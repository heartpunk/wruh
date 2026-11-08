# Concrete foreign wire specification checkpoint

Source: f81ec3511cbeb41084d3765de13e3a3c8eb50d9c.
Protocol, NativeBoundary, Bridge and Wire typechecked on NixOS, Lean 4.34.0,
with pinned dependencies. Exit 0; resources attached.

Terra 6.1 targeted review passed the tag/field equations and whole-frame bound.
Canonical 64-byte header plus payload, exact generation/stop identity, reserved
zeros, absent/present siginfo distinction, bidirectional exact codec obligations.
No actual codec/FFI implementation or codec proof has been supplied.

ForeignCall is only a type skeleton. The future extern must explicitly borrow
the request ByteArray and return an owned IO result, and its actual C ABI must
be verified against the pinned compiler/runtime, including initialization,
object layout, ownership and allocation failures. Reference checked:
https://lean-lang.org/doc/reference/latest/Run-Time-Code/Foreign-Function-Interface/
This moving documentation is guidance, not a pinned runtime proof. The @&
annotation has no ownership enforcement effect on the type alias itself.

Wire addressability does not establish operation validity, resource availability,
actual syscall effects or correctness of compiler/runtime foreign-call lowering.
