# Combined flags contract validation

Source: dc0c204d9a8017f4da306cc40ebcfb69c480dcfe.
Added only FlagsProtocolContract and its comment; existing definitions unchanged.
No proof or implementation added. FlagsArchitecturalLayoutCorrect approved by
user before this increment.

NixOS wruh-flags-contract-20261107 exited 0. Full Protocol.lean typechecked
from committed snapshot with Git metadata; command/resources: service.txt;
output: typecheck.log. Same pinned compiler and imports as flags-layout check.

Terra6.1 /root/review_flags_contract, medium reasoning, read-only: PASS.
All five existing Props conjoined unchanged. Identical preparation/loader/capture
arguments supplied to fidelity and frame obligations. No weakened obligation.
Executable invocation, record layout/decoder binding, private-memory separation,
and failure propagation explicitly remain integration obligations. Reviewer
performed no build or proof. Typecheck establishes well-typedness only.
