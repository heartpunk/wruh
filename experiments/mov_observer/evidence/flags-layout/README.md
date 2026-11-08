# Architectural flag layout validation

Source: 1b1c2c72d96878cb2569407b9c138c35ceba96d6.
Prop definitions only; no implementation change or proof.
NixOS wruh-flags-layout-20261107 exited 0. Full Protocol.lean typechecked
from committed snapshot with Git metadata; invocation/resources: service.txt;
output: typecheck.log. Same pinned compiler/cache as flags-boundary validation.

Terra6.1 /root/review_flags_layout, medium reasoning: PASS, no blockers.
Literal positions and canonical encodings match pinned VEX
fd41c675d50845b0aadd0b42ac7490038e2f3d82: guest_amd64_defs.h:319–324,
guest_amd64_helpers.c:918–965, libvex_guest_amd64.h:80–87.
FlagsMatchRflags is independent of the converters and mask. Decoder covers
all words; encoder relates all successful results. FlagsConversionCorrect
separately supplies availability/rejection/unmodeled-bit preservation.
Read-only review, no proof or build by reviewer. Typecheck is not a proof.
FlagsBoundaryClassificationCorrect was approved by user before this increment.
