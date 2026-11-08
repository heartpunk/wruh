# Shared frame refactor validation

Source: 7f2dae12b9c407c8df3e12c59eec2e2936835eea.
ProtocolInputStateFrame and ProtocolCaptureHandoffFrame reuse StateFrame,
with destinations obtained by map Prod.fst. Exclusion from that address list
is equivalent to inequality with every write destination. StateFrame moved
before its new uses; no intended semantic changes or new proof obligations.

NixOS wruh-frame-refactor-20261107 exited 0. Full Protocol.lean checked from
committed snapshot with Git metadata. Exact command/resources: service.txt.
Output: typecheck.log. Same pinned compiler and cached imports as frame-rename.
First transfer was blocked by SSH authentication; successful check followed
user key reload. FlagsProtocolFrames remains pending human review.
