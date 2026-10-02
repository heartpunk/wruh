# WRUH zeroth-pass corpus

Extraction: 19 PASS, 2 FAIL, 9 unselected.
Emitted canonical operation kinds: 23/31.

## Missing emitted operations

bv_sle, bv_slt, bv_udiv, bv_ult, bv_urem, const_array, sign_extend, zero_extend

## Selection and surviving coverage

- O0: 15 candidates; selected memcmp, division, extend, signed_shift, arithmetic, overlap, strcmp, branch, call, signed_branch, widths.
  Observed selection universe: 62 features; selection gaps: []; gaps after failed extraction: ['vex:Iop_128HIto64', 'vex:Iop_128to64', 'vex:Iop_64HLto128', 'vex:Iop_DivModU128to64'].
- O2: 15 candidates; selected strcmp, division, signed_shift, widths, arithmetic, loop, overlap, call, extend, signed_branch.
  Observed selection universe: 67 features; selection gaps: []; gaps after failed extraction: ['vex:Iop_128HIto64', 'vex:Iop_128to64', 'vex:Iop_32HLto64', 'vex:Iop_64HIto32', 'vex:Iop_64HLto128', 'vex:Iop_CmpEQ32', 'vex:Iop_DivModU128to64', 'vex:Iop_DivModU64to32', 'vex:Iop_Or64', 'vex:Iop_Shr64'].

## Failures

- O0 division: InventoryError: division: overlapping static block at 0x4010cb
- O2 division: InventoryError: division: overlapping static block at 0x40106a

## Limits and first-pass follow-up

- No native candidate execution or concrete input fuzzing occurred. Sources/templates are NOT approved for native execution.
- VEX set cover covers the observed seed universe plus explicit CFG requirements; it does not establish exhaustive inherited-angr operation coverage.
- Canonical operation occurrence is not validation of its denotation or value boundaries.
- Fresh instruction models were extracted; path composition and end-to-end semantic comparisons were not performed.
- Aliasing inputs, external ABI models, indirect calls, FP/vector behavior, faults, and shrinking remain untested.
- First follow-up: diagnose division CFG overlap; pin alias/overlap scenarios regardless of feature redundancy; audit selected native harness/input domains; run model-vs-binary input comparisons.
- Retain O0/O2 compiled ELFs and per-root fresh models from the declared JSON outputs.
