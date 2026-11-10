# FP checkpoint reviews

Both existing Astra light reviewers independently reviewed the source before
execution and the saved evidence afterward (2026-11-09).

Technical: source hashes match the successful run; twelve original and six FP
cases pass, exit 0; all eighteen raw FP images are 512 bytes. No blocker.

Telos/scope: meets the requested working FP path with a few concrete cases;
no proof detour or silent state narrowing. Documentation correctly limits the
x87 smoke checks rather than claiming exhaustive validation. No blocker.

Execution: NixOS, observer-fp-2.service, bounded child of fleet-build.slice;
see runtime.txt and run.log. Sources were edited locally and copied for build.
