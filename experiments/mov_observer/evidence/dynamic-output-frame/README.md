# State-indexed output permissions

Source: `2c6582892f30310c4bab6429fff88fcc537016c4`.

Pinned-runtime ownership investigation found that an owned return payload may
be allocated during a foreign call. Fixed output buffers required to be live
at every prefix cannot represent that case without forcing preallocation.

CallDynamicMemoryFrame permits state-indexed output slices, with the same
input preservation, write confinement and allocation-transition conditions.
Every output is live and writable in the PRE-state of a write. A later
allocation does not retroactively authorize a write. CallMemoryFrame remains
its constant-output specialization with the original conditions unchanged.

Terra 6.1 high /root/review_reply_terra performed a read-only source review
and found no blocker: it confirmed preservation of the fixed-output formula
and pre-state permission checks. It explicitly did not establish legitimate
ownership provenance for the projections, runtime allocation/header effects,
reference-root transfer, or concrete source/trace binding. Those remain open.

Integrated Lean 4.34.0 result and resource evidence are attached. Checked
Protocol, ContractEquivalence, NativeBoundary, Bridge, Wire, Transfer,
VectorProtocol, LegacyFp, FaultProtocol and WholeObserver using an exact Git
snapshot on NixOS, under fleet-build.slice, 2 GiB/no swap/one CPU. Existing
VectorProtocol style warnings remain. No observer implementation or proof added.
