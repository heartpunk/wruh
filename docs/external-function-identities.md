# External function identities

Function identities are nonempty strings. Decoded owners, root IDs and function
IDs, primitive symbols, summary function references, observation roots,
application roots/callees, and run roots preserve their exact spelling through
construction and JSON serialization. Leading underscores, punctuation,
whitespace, and Unicode are permitted. No stripping, escaping into another ID,
or Unicode normalization is performed. Ordering and duplicate/reference checks
continue to compare the exact strings.

This does not change the grammar of assignment names, summary/application/run
IDs, architecture/ABI tags, or primitive model/contract IDs. Existing valid
artifacts retain their schema and serialization.

The ELF provider uses CLE and pyelftools, which decode ELF symbol bytes with
UTF-8 replacement. Before accepting a rooted inventory, WRUH checks the raw
ELF spellings of selected/discovered function names and named direct-call
resolutions. A non-UTF-8 spelling that decodes to one of these names fails with
its byte representation and file offset. It must not silently alias another
symbol or a literal U+FFFD name. Unrelated non-UTF-8 names do not prevent
extracting a valid selected root. This is an explicit limitation of the current
string provider, not a claim that ELF forbids those byte names.

ELF names end at NUL. A provider's JSON string ID can contain NUL, but a byte
sequence after an ELF string's terminating NUL is not part of that ELF name.
Supporting arbitrary non-UTF-8 ELF names requires an explicit byte-preserving
provider/transport representation; this change does not introduce one.

`tests/test_symbol_identity.py` exercises real ELF inventory, CFG recovery,
fresh extraction, exact owners, JSON round trips, and artifact reference links.
Its `--artifact-only` mode exercises constructors/readers and raw ELF encoding
checks without importing the native symbolic runtime. Both modes include
independent expected strings and rejection controls.
