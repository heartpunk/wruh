# Bun function fixture

`napi_get_version.bin` contains 41 unchanged AMD64 bytes from Bun 1.4.2's
`napi_get_version`. `napi_get_version.rs` preserves its Bun-owned source definition.
The precise source revision, release archive, binary and excerpt hashes, original
address, and carve bounds are recorded in `provenance.json`.

Bun's upstream `LICENSE.md` states: “Bun itself is MIT-licensed.” That file is
preserved unchanged as `LICENSE.upstream.md`; `MIT.txt` supplies the standard MIT
permission text. No separate copyright notice appears in that upstream license
file. Attribution and source links are retained in `provenance.json`.

This excerpt is Bun's Node-API implementation. It contains no JavaScriptCore
code, external calls, or instruction-pointer-relative memory references. The
test relocates the complete function unchanged; its relative branches stay
inside the excerpt. The surrounding ELF headers, entry call, and padding are
synthetic test scaffolding. Nothing in the fixture is executed natively.

The regression removes the target symbol so it reproduces the symbols-only
inventory's omission of otherwise extractable target code. It first confirms
that the ELF loads and that only the synthetic entry is symbol-inventoried,
then requires recovered target identity, fresh extraction, exact instruction
coverage, and a canonical JSON round-trip.

The related BuildBuddy census used a different binary hash. Its successful
`napi_get_version` result corroborates the function choice; the committed bytes
are attributed to the upstream release rather than to that CI binary.
