# Binary representation ontology: discussion draft

This local draft is for discussion, not an approved schema or a prerequisite for the single-instruction property tests. `binary-representation.ttl` proposes classes and relations; `binary-representation-example.ttl` shows a small mapping, not an extraction output. Original census bytes remain unchanged. Repository IRIs and all names are provisional.

The example maps Apache occurrence 169 at canonical address 4562745 with bytes `01c0`; the candidate is `fn_0000000000059cb0`, image SHA-256 `7a850a2d913a2bcbc4a87b809b5362bc0a23a005e5590137abf42e997d7ca2d9`. The current draft catalogue classifies the bytes as XED `ADD_GPRv_GPRv_01` and iced code 7. Example identifiers are illustrative, not source identifiers. The source census and catalogue have distinct provenance: the former comes from Actions run 42073510694 at checkout `3757e9281b36fb914c24a731811c16eb4896e596`, and the latter is derived locally by the draft catalogue generator. The example does not claim these tools agree semantically or that any lifting is correct.

| Concept | Present source evidence | Further extraction or design needed |
| --- | --- | --- |
| Image and file | Census has binary identity and SHA-256, and archived function outputs are available. The exact Apache ELF has been located; availability of the other original binaries has not been established. | Explicit file, byte sequence and carrier identity with links to all relevant records. |
| ELF metadata and regions | Inventory reports candidates and symbols; source binaries contain ELF structures. | Complete parsed header/section/segment/symbol/relocation graph, exact file-byte and mapped-address relationships; don't equate file and memory extents. |
| Function candidate | Inventory records candidate ID, address, symbol and extraction outcome; aliases and inventory policy matter. | Explicit relationships from symbol entries and regions to candidates; no assertion that candidates are uniquely source functions. Bun's inventory is symbol-only. |
| Instruction occurrence | Successful FreshFunction artifacts record occurrence ID, address, bytes, architecture/mode, decoder text and image identity. | Explicit graph links and accurately scoped address-space identities; file offsets are not established by address alone. |
| Decoder classification | The draft catalogue computes XED and iced classifications of observed bytes with tool versions. | Model tool release and decode context explicitly; no cross-decoder or cross-version identity is assumed. |
| Lift and model | Extraction produces FreshFunction transition fragments, including guards, updates and targets. | Per-instruction lift/IR provenance and explicit model-content relationships require further extraction; a successful extraction alone does not establish a correspondence theorem. |
| Correspondence | An artifact or test can be evidence for a stated claim. | Claim relation, scoped assumptions, evidence, and any proof or validation must be made explicit. No representational, bisimulation or semantic-preservation claim follows merely from provenance. |

Source references: Wruh `791d033385c85b39c6cad8766db4c6f895f7a7a2`, `extractor/fresh.py` (`occurrence_catalog`, `extract_fresh_function`), `extractor/artifact.py` (`DecodedInstructionEvidence`, `Occurrence`), and `extractor/binary_census.py` (per-candidate extraction and ledger). Census execution checkout is the different SHA above; the existing run's original artifacts govern actual evidence. Source-specific details must be rechecked when materializing graph records.

## CCO and PROV commitments

The CCO Information Entity source at commit `be13b74cccf85617739c5288f9fdac805437386c`, `src/cco-modules/InformationEntityOntology.ttl`, declares version IRI `https://www.commoncoreontologies.org/2026-08-13/InformationEntityOntology`. Its `ont00000958` is Information Content Entity; `ont00001808` is `is about`; `ont00001938` is `represents`, a subproperty of aboutness with representational information content as domain and a carrier-characteristic isomorphism condition; `ont00001069` is Representational Information Content Entity, defined via that relation. Merely recording production or classification does not establish `represents`. The declared version IRI matches the pinned source, but direct HTTP dereference was not verified in this environment; an ontology catalog mapping the version IRI to a pinned local copy may be needed. PROV activity/entity links track provenance, not semantic correctness.

## Questions for joint review

1. Which specific relations and conditions should a claim scope support (for example, states, observation boundary, execution mode, and modeled environment), and which correspondence kinds are appropriate? The draft provides resources, not an invented closed taxonomy.
2. Which precise CCO `represents` assertions are justified by the intended encoding and model constructions, and what evidence warrants each? The draft deliberately does not infer them.
3. Should instruction encodings denote byte-and-mode types or particular binary regions? The draft treats them as byte-and-mode entities and keeps occurrences/regions distinct; identity rules need a decision.
4. What stable namespace, pinned CCO distribution, and import catalog should publication use? HTTP resolution of the version IRI remains unverified.
5. How should existing BFE terms and this draft be integrated without silently changing their semantics or asserting unrecorded extraction facts?
