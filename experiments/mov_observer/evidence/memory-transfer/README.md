# Memory-transfer obligation checkpoint

Source: fb48ebc01daef5c38af6ba723f78847d33efb400.
NativeBoundary, Bridge and Transfer typechecked on NixOS, Lean 4.34.0, using the
previous pinned observer dependencies. Exit 0; resource record attached.

Terra 6.1 reviewed the prefix/footprint increment. Revised obligations preserve
exact logical prefixes and endpoint frames without prescribing physical write
order or frequency. NativeWriteFootprint independently bounds actual touches.
Review found no prefix indexing/range defect in the revised increment.

Still open, not hidden premises: receipt authenticity, error causality,
nonvacuous availability, fixed footprint adequacy, wider-touch noninterference,
and environmental stability. The artifact-bound execution relation must retain
all actual runs; stability must be an explicit environment antecedent or the
specification must model concurrent interference. A stopped process token alone
does not freeze shared mappings. This checkpoint does not finalize that choice
or complete chunk 1. No observer implementation/proofs were added.
