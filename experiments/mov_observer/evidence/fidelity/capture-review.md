# Concrete MOV capture fidelity

MovCapturer.lean discharges ProtocolCaptureHandoffFrame and AccessCorrect for
the exact extracted sixteen-MOV capture, plus its one-step AccessSequence.
The result is exact GPR record fidelity, the concrete endpoint PC, preservation
of every other modeled field, and every byte outside the fixed capture record.
It quantifies over every post-state, with no admission predicate or new quotient.
It does not claim whole FP/vector/memory observation recovery or kernel behavior.

Parent review, installation-lane cross-review and independent LPS-worker review
passed. NixOS typecheck exited0; the three principal results depend only on
propext, Classical.choice and Quot.sound. Existing unchanged lower dependencies
were hash-checked against local source; current Bootstrap/MovInstaller were
rebuilt before checking MovCapturer. See check-capture.sh and capture-typecheck.log.
