# CPython extraction attempt counts

These results come from the completed CPython 3.12.14 all-symbol extraction attempt.

- Target: `libpython3.12.so.1.0`, SHA-256 `7e177a680eabb11fcb7d3867f7a1b9c4b93a9bd5b18129ce1af51ec07977b024`.
- WRUH started at `7b2f2fc7d456d2dc633ccfab085cc66159859ce9`; the session then committed the relocation fix `96a3d5f`, “Distinguish retained and runtime ELF relocations,” on its local `main`.
- Recorded environment: AYXG `9689144cf70c3923b9000a88473a65e408f0935b`, angr 10.0.1, Z3 5.1.0.
- Collection procedures are preserved in [[Collection scripts for WRUH extraction]].
- TODO recover and publish the relocation-fix commit and original run artifacts, then add immutable links here. Ask me for the archived extraction workspace: `/workspace/cpython-wruh/`, especially the inventory, per-function success/failure ledgers, loaded-image metadata, and models under `all-functions/`.

The unit is a unique symbol-bounded function entry address in `libpython3.12.so.1.0`. The attempt had 28,078 candidate addresses, of which 22,741 yielded extracted function models and 5,337 yielded recorded failures. Each failure-table category is the first observed extraction failure for its function; addressing one cause may expose another failure later in the same function.

| Outcome | Functions |
| --- | ---: |
| Candidates | 28,078 |
| Extracted | 22,741 |
| Failed | 5,337 |

| Remaining major mechanism | First-observed failures |
| --- | ---: |
| Noncanonical function-owner identifiers | 2,736 |
| Overlapping static blocks | 1,170 |
| Call fallthrough crossing the declared function extent | 1,000 |

| Tail | First-observed failures |
| --- | ---: |
| SMT export sort/width errors | 255 |
| Unsupported Z3 operators | 113 |
| VEX decode gaps | 38 |
| Unsupported CCall helpers | 10 |
| Unsupported Dirty helpers | 8 |
| Unsupported jump kinds | 3 |
| Symbol-extent problems | 2 |
| Miscellaneous symbolic-expression issues | 2 |

The 38 VEX decode failures count functions whose first observed extraction failure was decoding. The separate full-binary `vex_decode_sweep.py` report counts instruction sites, so its number uses a different unit.
