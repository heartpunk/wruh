# Observer flags composition obligation validation

Source: f1853fac839d97c93b0117635cdcd8d2de7c3fa7.
Prop only. No proof, runner implementation, or AYXG/native differential
comparison added or run. The intended goal is a faithful, noninterfering native
instruction observer; this statement composes the flags part of its semantic
obligations. Actual Lean/ABI execution correspondence remains separate.

NixOS wruh-modeled-e2e-20261108 exited 0. Full Protocol.lean typechecked from
committed snapshot with Git metadata. Command/resources: service.txt; output:
typecheck.log. Same pinned compiler/cache as flags-observation check.

Terra6.1 /root/review_modeled_e2e, medium reasoning, read-only: PASS.
Component contract conjoined, not assumed. Every loaded successor and every
target edge from that state covered; invalid flag classification unconditional.
Valid outcomes require capture existence and constrain every capture successor
by original metadata/flags, frame, exit PC. Composed input frame uses union of
stage footprints. No target-semantic correctness premise. Flags-only scope,
ambient GPR preservation and separate target progress accurately documented.
Reviewer did not build or prove. Typecheck is not proof of this proposition.
