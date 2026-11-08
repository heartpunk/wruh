# Legacy FP evidence specification checkpoint

Source: 3a7409dfdc42eaa856ccbd51e68bc3f921f0fcaf.
VectorProtocol and LegacyFp typechecked on NixOS, Lean 4.34.0, with the previously
pinned observer dependencies. Exit 0; resources attached. The imported vector
module emits two unnecessarySimpa style warnings.

Terra 6.1 targeted review passed: offsets, exact raw-image retention, independent
decode relation, wrong-length rejection, first-16 low-XMM correspondence, and
model field widths. Layout checked against native_probe.py and Linux v6.12
arch/x86/include/asm/user_64.h, user_i387_struct:
https://raw.githubusercontent.com/torvalds/linux/v6.12/arch/x86/include/asm/user_64.h
The record is the 64-bit legacy image, not a complete extended-state capture.

No numerical x87 conversion, FP installation, full native FP adequacy, or actual
acquisition binding is asserted. These remain required parts of chunk 2.
