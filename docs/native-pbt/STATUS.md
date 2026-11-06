# Native instruction differential testing: draft status

This draft is incomplete. Existing WRUH relations are extracted for exact
encoded operands and reused across concrete input states. The QuickJS-only
catalogue sweep extracted all 4,404 rows across 177 iforms; the catalogue is
being expanded to all completed functions from the latest successful main
census run. No suite-wide native campaign has yet run.

The bubblewrap runner has been exercised on three QuickJS catalogue encodings:
a register move, a memory load, a memory store, and an XMM operation. Their captured GPRs, RIP,
flags, two data/stack pages and the read-only code page matched the extracted relation.
A RIP-relative load through an additional mapped page also matched. On this
host the comparator also maps the sixteen FXSAVE XMM registers. The test host lacked XSAVE; its 512-byte
legacy FXSAVE state was captured explicitly. This is an integration check,
not a coverage or general correctness claim. A separate divide-by-zero fault
check also matched after explicitly comparing the fault-frame resume flag (RF);
its expected value follows the [Intel system programming manual](https://cdrdv2-public.intel.com/843857/253669-sdm-vol-3b-dec-24.pdf)
and the [AMD64 system programming manual](https://www.amd.com/content/dam/amd/en/documents/processor-tech-docs/programmer-references/24593.pdf).

The campaign attempts every catalogue row. Hypothesis varies register bindings,
immediates, address encodings, GPRs, six arithmetic flags, the direction flag,
and a 64-byte pattern placed near the center of each data/stack page. Each
changed encoding is re-extracted. RSP is fixed at `0x200800` when used in a
memory address; other address registers are adjusted to target the data page.
The driver checks iced Code, XED iform and recorded XED operand width.

Memory outside the two generated regions starts at zero, including up to two
automatically mapped extra pages. FS/GS bases are sampled from zero or the two
observed pages. The sixteen XMM inputs are generated; other extended-state
inputs are inherited from the runner. Initially generated examples and per-row
time are bounded; Hypothesis may execute additional cases during replay and
shrinking. These are input bounds, not claims of exhaustive coverage.

Known gaps before the campaign can be considered complete:

* XSAVE-format vector changes, other floating-point state changes,
  and native faults other than integer divide
  errors are currently reported as INCOMPLETE rather than compared.
  Architecturally undefined flags are excluded from comparison and reported;
  MATCH does not claim those flags were validated.
* Repeated string instructions and `ENTER` require multi-access memory modeling
  and are reported as INCOMPLETE.
* Native address calculations requiring more than two extra pages, addresses
  outside the supported lower-canonical range, or writes to the read-only
  instruction page are reported as INCOMPLETE. Memory preflight relies on iced-x86 access metadata; it is not
  an independent check of that metadata. The input constructor does not solve
  general address constraints. FS and GS bases are controllable; a load through
  each segment base has been checked end to end.
* The expanded suite catalogue has not yet been consumed; width alternatives
  are represented by separate catalogued iced Codes, not assumed equivalent.
* Native capture and the campaign need integration into the repository's normal
  build and test targets, and the whole campaign needs to run under the bounded
  fleet environment with its ordinary logs and Hypothesis database retained.
* Each incomplete or failed case must be investigated; a seed extraction or
  narrow integration check does not establish differential correctness.

The generator uses the sibling catalogue's XED helper protocol (hex on stdin,
iform and operand width separated by a tab). It verifies both the seed and
mutated encoding against iced Code, XED iform and recorded XED operand width. A valid XED iform alone is not evidence
that an operand binding, a model, or a native run is supported.

## Why a seed relation is not yet a form model

The current extractor steps a concrete decoded instruction.[^extractor] An aliased seed
such as `mov rax, rax` has no RAX update in the extracted relation, while
`mov rax, rbx` does. A transformation of the first result cannot recover the
distinct destination and source roles solely by renaming state symbols. The
extractor also does not currently record which IR constants came from encoded
immediates, so substituting constants by value can alter unrelated constants.
For this pass, each concrete binding is extracted separately, and the resulting
relation is reused across input states. No broader equivalence between operand
encodings is assumed.

[^extractor]: `wruh` at `7832cf2757d75d94d98a4f07291e3cf94e0168e3`, `extractor/amd64_state.py`, `step_instruction_outcomes` and `_post_updates`.
