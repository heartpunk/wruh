# Ontology design review log

Reviewers assessed the proposed vocabulary for scope, semantic fit, complexity, PROV-O alignment, open-world handling, and fidelity to the Lua, QuickJS, and CPython census evidence. Rounds 1–3 reviewed the interpreter-specific draft; Round 4 accepted its generic binary revision; Round 5 accepted the Bazel/Nix build-lineage extension. Review was read-only; no extraction or build was run.

## Round 1 — initial draft

**Status:** complete; revisions applied; Round 2 pending.

Two independent reviewers found the PROV-O specialization and overall scope sound, and agreed that `censusGeneratesEntry` supplies the needed link from a census activity to run-scoped records. They did not accept the exact draft yet.

### Findings and resolutions

1. **Identifier domain caused an OWL type conflict.** `ie:identifier` had domain `prov:Entity`, so using it on an `ExtractionCensus` or `FunctionExtractionAttempt` implied that activity was also an entity; PROV-O makes those classes disjoint. **Resolved:** removed the domain assertion and documented that an RDF subject IRI can identify an activity.
2. **The initial outcomes did not preserve source wording.** Lua reports blocked candidates; QuickJS and CPython reports use failed. **Resolved:** added distinct local `Blocked` and `Failed` individuals, plus `reportedDispositionLabel` for exact source text. Their labels are not equated or treated as a root-cause taxonomy.
3. **The meaning of excluded was underspecified.** **Resolved:** `Excluded` now means a candidate remains in the reported inventory but is explicitly withheld from extraction; pre-inventory screening belongs to the inventory policy. `NotAttempted` means no attempt is recorded and the candidate is not explicitly excluded.
4. **The QuickJS identity assertion exceeded recovered local evidence.** Its preserved run note establishes the 1,420-entry inventory but not the exact identity scheme. **Resolved:** the design now treats the QuickJS scheme as unresolved; `InventoryIndex` remains a possible local value without assigning it to QuickJS.
5. **The two CPython evidence sources were too easy to conflate.** The all-functions 3.12.14 counts are secondary and the original workspace/transcript are unrecovered; open-boundary evidence is from a separate selected-function 3.12.13 run. **Resolved:** the ontology rationale now states these limits together with the claims they qualify.
6. **RuntimeImage mentioned unmodeled mappings.** **Resolved:** removed mappings from the class definition; first-pass membership covers binary objects only.
7. **The import IRI was normalized.** The ontology now imports the W3C ontology IRI `http://www.w3.org/ns/prov#`, matching the PROV-O term namespace declared by the W3C Recommendation. The version-specific public vocabulary namespace remains provisional.

The reviewer also reminded us that OWL domain/range axioms classify resources; they are not record validation. The draft retains open-world semantics and leaves cardinality/count checks outside the ontology.

## Round 2 — revised draft

**Status:** complete; both reviewers accept the revised ontology as a good first pass; final wording check pending.

Both reviewers confirmed the Round 1 resolutions: the PROV-O mappings and current import are coherent; `identifier` no longer asserts Entity for activities; disposition wording preserves source labels; QuickJS's unresolved identity mechanism and the separate CPython evidence scopes are explicit; and the model remains open and appropriately scoped. One reviewer recommended defining the identity-basis examples and keeping the source-label mapping explicit and evidence-backed. These are incorporated in the next wording pass.

The user clarified that limited historical CPython evidence must not constrain future coverage. The design now states that it is meant to represent a full census for every candidate under the declared inventory, all attempts/retries and observations, and all generated artifacts; the CPython archive limitation applies only to historical claims. Two reviewers will check this final coverage wording.

## Round 3 — full-census coverage wording

**Status:** complete; both reviewers accept the first-pass design.

Both reviewers confirmed that the ontology supports a complete future census for every candidate in a declared inventory, with all attempts, observations, and artifacts, and that the recovered CPython limitations apply only to claims about historical runs. They also accepted the identity-basis definitions, the source-faithful open dispositions, and the explicit caution against inferring `incomplete` from a `failed` or `blocked` label alone.

The reviewers noted one stale sentence in the README's review record. It has been corrected to match the completed third round; this was a documentation consistency fix and did not change the ontology model.

## Resolution after Round 3 (prior version)

At the end of Round 3, the interpreter-specific first-pass design was accepted by both reviewers. Round 4 generalizes that accepted model and adds inventory-generation provenance; both reviewers accept the revised generic version as recorded below. Keep the namespace provisional until a durable public IRI and versioning policy are selected. Extend the ontology only when a concrete target or data exchange requirement demonstrates a needed concept not already represented.


## Round 4 — generic binary model and inventory-generation provenance

**Status:** both reviewers accepted the model; their wording recommendations are incorporated.

This revision generalizes the base target from interpreter runtime images to `AnalyzedImage` and makes interpreter targets an `InterpreterImage` specialization. It adds `InventoryGeneration` as a PROV-O activity that uses the analyzed image, an explicit `InventoryPolicy`, and exact `ToolRelease` entities, then generates a `FunctionInventory`. The usage convention records distinct angr and WRUH release/revision entities for WRUH-based inventory generation; the census consumes that generated inventory. Reviewers accepted the genericization and provenance path. Their recommendations are applied: exact tool releases are recorded on every census/attempt activity that uses them; same-image matching is stated as a dataset-level validation convention; and out-of-scope future supply-chain/SARIF suggestions were removed from the design summary. Neither reviewer found an ontology blocker.


## Round 5 — Bazel/Nix build lineage

**Status:** complete; both reviewers accept the extension.

This revision adds `BuildActivity` as a PROV-O activity. It records build inputs, exact tool releases, and generated binary objects, analyzed images, or locally built tool releases. The design is grounded in the repository's Bazel module/lock files and Nix flake/lock and angr integration, while explicitly avoiding a source-to-function mapping or an assertion that every historical target used the current workflow. Both reviewers accepted the PROV-O domain/range choices, the build-to-image/tool provenance path, and the separation between recorded build provenance and package supply-chain modeling. Their optional wording suggestion is incorporated: an activity can generate one or more of the applicable output types according to the evidence.
