# Actual CPython FP arithmetic extraction

WRUH snapshot: 584d4344; AYXG f27e3824; angr-nix 52f1b965.
Supported Nix/Bazel/REAPI build completed successfully: 66 actions, 70.990 seconds.
The enclosing job subsequently failed in a newly added smoke-test API-name check; that failure does not invalidate the successful extraction outputs, and the test is being corrected/rerun separately.

| Root | Occurrences | Local edges | Shared DAG nodes | Arithmetic node |
|---|---:|---:|---:|---|
| float_add | 119 | 144 | 1490 | fp_add |
| float_mul | 120 | 145 | 1493 | fp_mul |

Both use the same exact pinned CPython closure, 91 state declarations, bit-backed storage, and explicit unresolved transfer boundaries as previous extraction evidence. Full unchanged artifacts are retained as gzip. No candidate native execution.
The optional Unicorn engine emits a loading diagnostic; the extraction uses the VEX engine, and the artifacts were produced successfully. CLE reports relocation 36; the loaded-image model retains unsupported TLS descriptor initialization as an explicit unknown range rather than invented concrete bytes.
Final integrated preservation/exporter checks remain outstanding.
