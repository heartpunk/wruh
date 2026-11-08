# Vector obligation checkpoint

Source: 832bb08f37d96d9aa35a178708dd2137ce538765.
VectorProtocol.lean typechecked on NixOS, Lean 4.34.0, against approved Protocol
474813899b9a01768924704941c1c2e353099fee and pinned observer dependencies.
Exit 0; two unnecessarySimpa style warnings, no errors. Resource record attached.

Terra 6.1 reviewed full modeled field enumeration (32 ZMM, 8 masks), low-bit
XMM/YMM views, 2112-byte independent little-endian relation, decoder completeness,
all-input/all-result stages, preservation of GPRs/flags/non-vector FP fields,
and the added protected-memory separation obligation. Targeted review passed.

Native profile/exact instruction binding, intermediate/fault effects, protected
set adequacy, and full FP/x87 representation remain unfinished. No observer
implementation or correctness proof was added. This is the vector part of chunk
2, not a claim that chunk 2 or the whole goal is complete.
