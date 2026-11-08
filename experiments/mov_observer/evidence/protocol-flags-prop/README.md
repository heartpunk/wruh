# Modeled flags fidelity obligation validation

Source: 5e869afd346d2e2b4ba32823c262d373ccf01413.
No proof, axiom or sorry added. Existing proof statements unchanged.

## Typecheck

NixOS unit wruh-flags-prop-20261107 exited 0. Full Protocol.lean checked
from committed snapshot with usable Git metadata. Exact command, compiler
path and resources: service.txt. Full output: typecheck.log. Reused unchanged
compiled dependencies documented in ../protocol-input-memory-frame/README.md.
Typecheck establishes well-typedness, not truth of the new obligation.

## Astra light review

Agent /root/review_flags_prop; gpt-6-astra, low reasoning. Source-only review.
No blocker for the Prop-only modeled obligation. Six one-bit flags and raw
64-bit d/ac/id match the current context. Availability and universal successor
clauses exclude disabled guards and reject-all decoders. Decoder receives only
captured memory, no requested state or model prediction. Capture compares with
post before RIP redirection. No fidelity conclusion is assumed.

## Remaining specification boundaries

Not ready as a concrete native implementation contract. Preparation is still
an unrestricted function: its own frame must prevent direct flag installation
or other unintended changes. Frames, record layout, native admissibility and
concrete extraction binding remain open obligations. Arbitrary 64-bit d/ac/id
values must not be claimed representable in native RFLAGS without establishing
the model-to-hardware encoding. Missing architectural flags remain open too.
These require specification work, not silent implementation choices.

Reviewed Protocol.lean: ModeledFlags, observeModeledFlags,
ProtocolFlagsFidelity; models/Extracted.lean: Γ and flag variables;
Pipeline.lean: prepareInput and enterCapture, all at source revision above.
