# Bridge specification checkpoint — not chunk completion

Source checked: 0012a529f615cbeec1411c1f901e190159ef47cd.
NixOS, Lean 4.34.0; NativeBoundary.lean then Bridge.lean; exit 0.
Imported Protocol from checked 474813899b9a01768924704941c1c2e353099fee;
remaining dependencies from the existing pinned observer cache.
2 GiB / no swap / one CPU under fleet-build.slice. See resources.txt.

Terra 6.1 source review confirmed register layout, independent architectural
flag correspondence, bounded buffer addresses, optional siginfo, and the
accessibility direction in CallTerminates. Review does NOT approve a completed
native bridge. Remaining review items:

- Give allocation incarnations identity, account for allocation/free events,
  and prevent omitted intermediate effects from invalidating lifetime claims.
- Separate writable payload from object metadata; require complete accounting
  of relevant host memory and distinct bridge/runtime scratch footprints.
- Tie buffers to actual marshalling and constrain operation-specific transfers,
  including partial/error results and the intended process/stop identity.
- Bind execution semantics to actual future Lean/foreign artifacts, covering
  abort/blocking/error paths; prove whole-orchestrator termination, not only calls.

No observer implementation or observer correctness proof was added.
