# Flags memory separation validation

Source: c05e9435c6552aa5472ab0eed546e52e7f62cc84.
Prop only, integrated using same base and footprints as decoder/frame contracts.
NixOS wruh-flags-separation-20261108 exited 0. Full Protocol.lean checked
from committed snapshot with Git metadata. Command/resources: service.txt;
output: typecheck.log. Same pinned compiler/cache as record-contract check.

Terra6.1 /root/review_flags_separation, medium reasoning, read-only: PASS.
Correct final valid base and offsets 0–7; implication applies to union of all
three footprints. No unnecessary pairwise disjointness. Shared arguments
correctly integrated. Diff limited to predicate, parameter/conjunct and comment.
Protected-set adequacy, actual privacy and record writer agreement are not
proved by this relation; choosing False does not establish actual protection.
No proof or build performed by reviewer. Typecheck is not a proof.
