# Exact extraction-environment CPython lifting

## Identity and successful extraction

Source revision: `aa9a5d8124d7ad183ccdbee1e58b294fcdcd9cdb`.
Frontend: NixOS; execution: repository-configured Bazel/REAPI.
CPython: 3.12.13, GCC 15.2.0, shared non-debug build, exact build arguments in `identity.json`.
All five declared ELF inputs are SHA-256 checked. The interpreter executable is identified and verified; the analyzed image contains libpython, libc, libm and the loader, at explicitly selected deterministic mappings.

| Function | Instruction occurrences | Local STS edges | Shared DAG nodes |
|---|---:|---:|---:|
| PyBytes_Size | 22 | 23 | 382 |
| PyObject_Call | 75 | 82 | 1090 |
| PyFloat_AsDouble | 168 | 191 | 1926 |

Command in the frozen Linux snapshot:

```sh
nix develop --no-write-lock-file --command scripts/bazelw build --config=reapi --keep_going \
  //extractor:open_transfers_check //extractor:open_object_check \
  //extractor:cpython_extract_PyBytes_Size \
  //extractor:cpython_extract_PyObject_Call \
  //extractor:cpython_extract_PyFloat_AsDouble
```

Exit 0; Bazel elapsed 53.243 seconds. Full DAG artifacts are gzip-compressed here without changing their contents. Each successful action's runtime trace is retained; interpreter hash, version and build metadata match the identity-establishing trace. Independent read-only review checked DAG references/topology, complete 91-variable updates, containing-image provenance and initialization byte lengths.

## Exact boundaries

Only selected function bodies are extracted. Direct callees outside selection and indirect transfers remain explicit open boundaries with original symbolic target and post-state. No whole-interpreter composition or native candidate execution is claimed. Initial-image data is separate from instruction semantics. Unresolved relocation, pending resolver and CLE-skipped TLS descriptor ranges override concrete segment bytes; a TLS descriptor occupies 16 bytes. This is not a running dynamic linker or initialized CPython process state.

## FP arithmetic follow-up

`float_add` and `float_mul` from the same libpython were attempted at WRUH revision `4391c7a6`, with AYXG Python FP transport `09169378`. Both failed in angr 10.0.1's public SMT exporter: conversion operators emit explicit mantissa width rather than SMT-LIB significand width (binary64 `to_fp 11 52` instead of `11 53`). No arithmetic extraction success is claimed. Existing six O0/O2 corpus models still extracted successfully in that run. Exact diagnostic support is committed at `c23798ca`.

FP arithmetic completion and final AYXG Lean/Python correspondence remain outstanding. SMT floating-point models do not automatically recover NaN payload propagation or hardware FP exception state.
