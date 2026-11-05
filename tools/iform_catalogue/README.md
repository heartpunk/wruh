# Instruction-form catalogue

`generate.py` reads every occurrence in every successful function artifact from
one or more complete, unsampled binary censuses. It checks each ledger against
its archive and verifies the archive digest and occurrence image identities. iced-x86 and
XED must each decode exactly the recorded instruction bytes in AMD64 long mode;
any undecodable instruction stops generation rather than disappearing silently.
Rows aggregate identical bytes and iced Code while retaining every function,
canonical address, static occurrence ID, target ID, and binary digest.
Different encodings remain separate rows even when they share an iform. `operand_width` is XED's decoded
effective operand width in bits; it is not a list of all operand widths.

On x86-64 Linux, use XED 2026.07.15 from `shell.nix` and iced-x86 1.21.0.
The Linux wheel used for the checked-in catalogue is the cp38-abi3 manylinux
x86-64 wheel with SHA-256
`489789377bfc1fe432bd2a8a5780c9f3e7c35be2e6133b0de5432cd901cad32c`.
The pinned wheel is supplied by `shell.nix`; no separate `PYTHONPATH` setup is
needed. On x86-64 Linux, enter `nix-shell tools/iform_catalogue/shell.nix`
and run:

```sh
cc -O2 -Wall -Wextra -I"$XED_ROOT/include" tools/iform_catalogue/xed_decode.c "$XED_ROOT/lib/libxed.a" -o /tmp/wruh-xed-decode
python tools/iform_catalogue/generate.py \
  --census data/iform-catalogue/quickjs --census data/iform-catalogue/lua \
  --census data/iform-catalogue/bun --census data/iform-catalogue/apache \
  --xed /tmp/wruh-xed-decode --output data/iform-catalogue/catalogue.jsonl
```

The catalogue records observations from the successful extraction artifacts,
not coverage of all executable instructions or a semantic correctness claim.
Failed census candidates are not included. The adjacent JSON-LD context is
required when interpreting individual JSONL rows as JSON-LD.
