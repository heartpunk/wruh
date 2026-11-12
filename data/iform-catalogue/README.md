# Golden census instruction catalogue

This manually selected snapshot contains the four completed target reports from
[GitHub Actions run 42073510694, attempt 1](https://github.com/heartpunk/wruh/actions/runs/42073510694), obtained from that run's BuildBuddy execution outputs. The run was triggered by PR #87 at head `7832cf2757d75d94d98a4f07291e3cf94e0168e3`; the actual Wruh extraction checkout recorded in each report was GitHub's synthetic merge `3757e9281b36fb914c24a731811c16eb4896e596`, merging main `791d033385c85b39c6cad8766db4c6f895f7a7a2` with that PR head. The extraction SHA is not the later catalogue commit.

The reports record AMD64 Linux targets built from Nixpkgs revision
`e79d204daf01f8a877f7b2ce7324874ce9c84676` with `dontStrip=true` and AYXG
`324752afe80b05d7fd8854834725cf5ee360f173`. Each subdirectory retains its
original ledger, summary, JSON-LD graph, progress and function archive. The
summary hashes authenticate the downloaded graph and archive; `entries.jsonl`
records the disposition and artifact reference of every candidate.

| Target | Version | Binary SHA-256 | Extracted | Failed |
| --- | --- | --- | ---: | ---: |
| QuickJS qjs | 2026-06-04 | `1f3599bc3fbbb53b396e2e9ab381c6e20a34a4e49fe564dfb6c95bead928da9e` | 223 | 52 |
| Lua liblua | 5.5.1 | `16bf574842a00c95367de74b9c086cd5fa3695c6c5b1e741a03c892e29e6bd94` | 507 | 214 |
| Bun | 1.4.2 | `62fbc811a40e3ad0c0fc4bde563d4cac4383cde27133420f19896e1edf00d62e` | 182 | 488 |
| Apache httpd | 2.4.69 | `7a850a2d913a2bcbc4a87b809b5362bc0a23a005e5590137abf42e997d7ca2d9` | 911 | 249 |

Bun's Nixpkgs package used a prebuilt Bun binary. Its census used only defined,
sized ELF function symbols from the main object; it did not use CFGFast discovery.
The completeness of those symbols as a set of Bun functions is not established.

The GitHub Actions run remained in progress when these four reports were
collected. CPython and Node reports had not been obtained and are not represented
in this snapshot. This is not a claim that those targets have no successful
functions. The combined catalogue retains
each occurrence's target ID, binary digest, function ID, canonical address and
static occurrence ID, and is limited to the successful function artifacts.
Failed candidates and instructions outside the census inventory are not covered.
See `tools/iform_catalogue/README.md` for the decoder versions and regeneration.

The generated JSONL has 25,102 distinct byte encodings, 277 XED iforms and
299 iced Codes, with 96,423 occurrences: 45,150 Apache, 25,674 Lua, 14,976
Bun and 10,623 QuickJS. Its SHA-256 is
`b721303d94d81e56244154fdb4cbefff93cbe11eb9f6de1da81d7c571980bcfc`.

Each target's `sources.jsonld` describes the five unmodified source files by
role, media type, byte length and SHA-256, tied to the source run and checkout.
The function archive is preserved as an evidence boundary: its embedded original
FreshFunction JSON documents are not rewritten or assigned invented semantics.
`catalogue-info.jsonld` describes the generated catalogue and pins both decoder
versions. See `vocabulary.ttl` for all terms and their intended meanings.

The [binary representation ontology draft](../../docs/proposal/ontology/binary-representation-notes.md) explores a CCO- and PROV-grounded model and distinguishes present evidence from future extraction. The contexts in this snapshot describe the existing catalogue and preserved source files; they do not yet materialize that proposed model.
