# Instruction discovery coverage

Fresh instruction relations describe the decoded instructions exactly within the
supported instruction semantics. Successful serialization alone does **not** prove
that every instruction reachable through arbitrary indirect control flow has been
discovered.

CFG roots and newly extracted fresh functions carry `extraction_coverage`:

- `scope: intraprocedural-jumps-only` covers the function's direct and indirect
  jumps. Calls and returns are separate transfer boundaries, not closure claims.
- `status: partial-indirect` means a discovered symbolic jump may reach additional
  internal instructions. `unresolved_indirect_sites` lists its instruction address,
  including when a loaded table provided some discovery seeds. Legitimate external
  destinations are still allowed by the instruction relation.
- `status: direct-cfg` means the walked CFG encountered no symbolic jump. It is a
  report about that traversal, not a proof about arbitrary entry addresses, all
  bytes in the symbol, callers, or whole-program reachability.
- `discovery: loaded-table-seeds-do-not-bound-symbolic-targets` makes the separation
  between discovery hints and instruction semantics explicit.

The existing fresh-function schema remains readable. The field is optional, so
old artifacts still roundtrip without it; missing coverage means unknown coverage,
never proven completeness. Consumers needing closure must not treat either a
missing field or `partial-indirect` as evidence of closure. Existing consumers
that ignore this additive field do not gain a completeness guarantee.

## Recognized loaded-table seeds

Open AMD64 extraction recognizes a contiguous RIP-relative 64-bit `lea` followed
by either `jmp [base + index*8]` or `movsxd target, [base + index*4]; add target,
base; jmp target`. The index must differ from the base register; the relative
load must not overwrite the base. No segment override is accepted.

The table base must identify an unambiguous sized ELF object in the same loaded
object. The object size bounds the table; it must be divisible by the entry width.
Absolute entries use the loader's 64-bit words; relative entries use signed 32-bit
offsets from the table base. Repeated entries are valid. An external entry does
not terminate scanning. Only targets inside the selected function and on decoded
instruction boundaries become local seeds. Their block boundaries are installed
before CFG walking, preserving the existing partition/alignment checks, including
when two table destinations share a tail.

These are initial loaded-image candidates, not an assertion that memory is
immutable or that the runtime index is bounded. Symbolic target expressions,
guards, and state updates remain unchanged. Unsized tables, unsupported instruction
sequences, other architectures, ambiguous object bounds, and unaligned candidates
do not acquire invented local targets. Their discovered symbolic jumps remain
explicitly unresolved. This deliberately limited recognizer is not a general
indirect-branch decision procedure.

The regression uses real ELF instruction bytes for an interpreter-style dispatcher
with two indirect-only handlers, duplicate entries, signed negative offsets, and
an external entry between local entries. It also covers a shared tail and rejected
recognition/alignment cases. It does not establish how often the pattern occurs in
CPython, nor explain the historical 1,170 overlapping-block census failures.

A table base hoisted into a persistent register far from the indirect jump is
outside this contiguous-pattern recognizer. A follow-on measurement should locate
the dispatcher in the pinned libpython image, retain its bytes/bounds/CFG trace,
and determine whether a bounded dataflow extension is justified. Synthetic success
does not establish coverage of that real interpreter pattern.
