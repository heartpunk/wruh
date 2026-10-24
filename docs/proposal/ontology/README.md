# First-pass binary function extraction ontology

**Status:** generic binary and Bazel/Nix build-lineage design accepted by two reviewers  
**Version:** `0.1.0-draft`  
**Scope:** provenance for binary function inventories, extraction censuses, per-candidate outcomes, and artifacts. Interpreter targets are a specialization of the generic binary target. Source mapping is outside this first pass.

## Decision

Use PROV-O as the only external ontology in the first pass. Specialize its `prov:Entity`, `prov:Activity`, and `prov:Collection` terms for analyzed binary images, inventory-generation activities, function inventories, candidates, census activities, attempts, and outputs. Interpreter-specific targets use the `InterpreterImage` subclass; generic binary targets use `AnalyzedImage` directly. Local terms express only concepts PROV-O does not define: candidate identity/address basis, inventory policy, run-scoped disposition, failure/interruption observations, and unresolved artifact boundaries.

The Turtle file is the machine-readable ontology draft: [binary-function-extraction.ttl](binary-function-extraction.ttl). Its GitHub-based term namespace is provisional. Resolve a durable namespace and publication/versioning policy before issuing external identifiers.

## Build and inventory provenance

The provenance chain starts before inventory generation. A `BuildActivity` (`prov:Activity`) records build inputs such as a source revision, build recipe/configuration, or dependency lock as `prov:Entity` inputs. It links exact build tools through `activityUsesToolRelease` and may generate any combination of binary objects, analyzed images, and locally built tool releases that its actual outputs establish. The analyzed image is a collection of its binary objects, so a census target can be traced through its members to the activity that produced them. This records build lineage; it does not map binary functions back to source code or claim that a build is reproducible.

For the WRUH project, the repository has both Bazel and Nix anchors: [`MODULE.bazel`](../../../MODULE.bazel) and [`MODULE.bazel.lock`](../../../MODULE.bazel.lock) describe the Bazel dependency graph, while [`flake.nix`](../../../flake.nix) and [`flake.lock`](../../../flake.lock) describe the Nix development/build environment and locked inputs. The flake selects Bazel 9 on Linux and Bazelisk on macOS, and the Nix environment supplies angr. [`tools/nix_native_deps.bzl`](../../../tools/nix_native_deps.bzl) connects Bazel to immutable Nix store outputs; [`scripts/stage-angr-nix`](../../../scripts/stage-angr-nix) pins the angr-nix source revision. These files ground the vocabulary choice, but do not imply that every historical target binary was produced by this exact workflow. Capture the exact Bazel/Nix versions or revisions actually used in each activity instead of inferring them from a moving name; see [the build provenance evidence note](../evidence/build-provenance.md).

A `FunctionInventory` is a generated result, not an unexplained input list. Represent its provenance as:

1. A pinned `AnalyzedImage` identifies the executable and any other binary objects included in the analysis target, with digests and target build/platform metadata where available. Where build evidence exists, the image and/or its member binary objects link to their `BuildActivity` provenance.
2. An `InventoryGeneration` (`prov:Activity`) uses that image, a declared `InventoryPolicy`, and one or more exact `ToolRelease` entities.
3. For a WRUH-based inventory, record separate tool-release entities for `angr` and WRUH. Record the exact `angr` release/build identifier and exact WRUH revision (prefer a full commit ID); link both to the `InventoryGeneration` activity. Do not bake current release values into the ontology. When these tools were built or realized locally, their `ToolRelease` entities can also be outputs of a `BuildActivity` that records the applicable Bazel/Nix tools and inputs.
4. The inventory-generation activity generates a `FunctionInventory` (`prov:Collection`), which contains its `FunctionCandidate` members. Its policy describes the candidate unit, identity/alias rules, extent rules, and screening/exclusion behavior.
5. An `ExtractionCensus` uses the analyzed image and generated inventory, then generates run-scoped `CensusEntry` records. Record the tool releases used by the census and by each `FunctionExtractionAttempt` on those activities with `activityUsesToolRelease`, including exact WRUH revisions where applicable. Each entry can link zero or more distinct attempts, their artifacts, and observations.

The graph therefore exposes `BuildActivity → AnalyzedImage/BinaryObject/ToolRelease → InventoryGeneration → FunctionInventory → ExtractionCensus → CensusEntry → FunctionExtractionAttempt → ExtractionArtifact/observations`, with build inputs and tool releases attached to the activity that used them. Use `prov:wasAssociatedWith` for the responsible software agent when known; a tool release identifies software used, not the agent that ran it. If there are multiple build or inventory stages, preserve them as separate activities, link their actual intermediate entities, and use `prov:wasInformedBy` when one activity informed another rather than collapsing the provenance. Dataset-level validation should confirm that the census uses the image from which its inventory was generated; OWL does not enforce that identity.

## Coverage target

The ontology is intended to describe a complete census of every candidate selected by a declared target inventory, whether the target is an interpreter image or another binary image. A full census can contain one `CensusEntry` per inventoried candidate, zero or more distinct attempt activities per entry, all observed diagnostics/interruption/boundary records, and every generated artifact. The first-failure pointer is a report summary; it does not replace later failure observations or retries. Inventory membership and entries provide a countable ledger without baking in a maximum size or success threshold.

The limited recovered interpreter evidence constrains claims about those historical runs, not what the ontology can represent. The ontology supports future complete inventories, per-candidate records, retry history, and detailed observations for other binary targets too.

## Questions the first pass must answer

1. Which build activities, build inputs, build-tool releases, analyzed binary objects/image, inventory policy, and analysis-tool releases produced a function inventory?
2. What candidate unit and identity basis defined its denominator, and what address space and extent were recorded?
3. Which image and inventory did a census use, and for every candidate what disposition was reported, what attempts occurred, and what artifacts or observations resulted?
4. Which blockers were first observed at which stage, and which outcomes were interruptions such as timeout or OOM?
5. Which transfer, relocation, initialization, or other boundaries remain open in an artifact?

## Core terms

| Local term | PROV-O alignment | Meaning |
| --- | --- | --- |
| `AnalyzedImage` | `prov:Collection` | Pinned set of binary objects analyzed together. It does not mean a live initialized process. |
| `InterpreterImage` | subclass of `AnalyzedImage` | Interpreter-specific target specialization; implementation identity is recorded only for this subtype. |
| `BinaryObject` | `prov:Entity` | Executable, shared object, or other binary object in the image. |
| `BuildActivity` | `prov:Activity` | Evidenced build or realization event that can generate binary objects, analyzed images, or tool releases. |
| `InventoryPolicy` | `prov:Entity` | Candidate selection, identity, alias, extent, and screening rules. |
| `InventoryGeneration` | `prov:Activity` | Applies a policy to an image using identified tool releases to produce an inventory. |
| `ToolRelease` | `prov:Entity` | Exact tool version or source revision used by an activity; includes build tools such as Bazel/Nix and analysis tools such as angr/WRUH. It is separate from the responsible `prov:SoftwareAgent`. |
| `FunctionInventory` | `prov:Collection` | Generated candidate universe used as the census denominator. |
| `FunctionCandidate` | `prov:Entity` | Target-specific extraction unit, without asserting source-level or semantic uniqueness. |
| `ExtractionCensus` | `prov:Activity` | Activity analyzing an image and reporting outcomes for an inventory. |
| `FunctionExtractionAttempt` | `prov:Activity` | One attempt; retries remain distinct activities. |
| `CensusEntry` | `prov:Entity` | Run-scoped record connecting candidate, disposition, and attempt history. |
| `ExtractionArtifact` | `prov:Entity` | Output of an attempt, without an implied completeness claim. |
| `FailureObservation` | `prov:Entity` | A diagnostic/blocker observation, not an inferred root cause. |
| `InterruptionObservation` | `prov:Entity` | Resource/worker/host interruption, kept distinct from semantic failure. |
| `OpenBoundaryObservation` | `prov:Entity` | A transfer, relocation, initialization, or other boundary retained by an artifact. |

The initial local disposition values are `extracted`, `blocked`, `failed`, `incomplete`, `excluded`, and `not_attempted`. They are open values, not a closed enum. `blocked` and `failed` preserve source-report wording; the ontology does not equate them. Do not infer `incomplete` from a source label of failed or blocked alone; that mapping requires evidence that the attempt did not reach a completed outcome. `excluded` means the candidate remains in the reported inventory but the run explicitly withholds it from extraction; candidates screened out before that inventory are described by the inventory policy. `not_attempted` means no attempt is recorded and the candidate is not explicitly marked excluded. An exact source label can be kept separately. Failure stage/code and boundary kind remain string-coded in this first pass because the recovered runs do not establish one complete, stable taxonomy.

## Fit to recovered runs

The retained interpreter evidence demonstrates at least two distinct candidate identities: Lua uses distinct sized symbols, and CPython uses unique symbol-bounded entry addresses. The recovered QuickJS note establishes 1,420 inventoried function records but does not independently establish the identity mechanism; its scheme stays target-specific and unresolved until the inventory is recovered. The ontology offers an inventory-index value without asserting that QuickJS used it. These bases must not be collapsed into one nominal “function ID” or treated as equivalent denominators. Address values therefore carry an explicit address-space designation; a missing/unknown space stays unknown. The address-space labels distinguish file byte offsets, object-file virtual addresses, image-relative values, runtime mapping addresses, and values whose coordinate system is unknown.

The Lua and QuickJS run notes, plus the secondary CPython all-functions note, show distinct outcome labels and first-observed failure counts. The all-functions CPython artifact and transcript remain unrecovered, so its 3.12.14 counts are not independently audited here. The unresolved transfer and relocation/TLS examples come from a separate, selected-function CPython 3.12.13 run; they motivate the open-boundary term but are not evidence about the all-functions census. A `CensusEntry` is separate from an actual attempt so excluded and not-attempted candidates in the reported universe can still be counted; pre-inventory filtering remains part of the stated inventory policy. An interruption is separate from a failure/blocker observation, and an open boundary is separate from failure. These historical examples motivate the initial model; they do not limit its use to interpreters.

## Design constraints

- **Reuse exact terms.** PROV-O is an OWL ontology for provenance; its entities, activities, agents, collections, usage, generation, association, and timing terms fit this scope directly. Local specializations express only extraction-specific meanings.
- **Keep the scope narrow.** This models build lineage at the artifact/activity level, binary target identity, inventory provenance and units, census outcomes, diagnostics, artifact provenance, and retained boundaries. It does not model source-code structure or function mappings, instructions, CFG topology, symbolic machine states, path constraints, SMT theory, proof obligations, security findings, or whole-program semantics.
- **Leave the vocabulary open.** No exhaustive failure hierarchy, status closure, disjointness, uniqueness key, or cardinality axioms are asserted. Different targets can preserve divergent inventory policies and future observations can add new values.
- **Do not treat OWL as a ledger validator.** OWL uses open-world semantics. Absence of an entry or observation does not mean `not_attempted`, zero, success, or complete. Dataset-level validation must check one entry and one reported terminal disposition per selected candidate, reconcile counts, confirm the census and inventory-generation activity refer to the same image, and detect missing artifacts.
- **Keep reported observation apart from cause.** Failure categories, stage, and raw diagnostic describe what a run recorded. They do not claim a root cause unless separately evidenced.
- **Preserve process versus software identity.** PROV-O associates an activity with a responsible agent and separately describes entities it used; a tool release is not the executing agent.
- **Defer the namespace decision.** The current IRI base points at the proposed repository path and `main`; it is marked provisional. Do not publish it as a stable public vocabulary until a durable namespace and versioning policy are chosen.

These constraints follow established ontology-design guidance: define scope and competency questions first, reuse existing terms where their meanings fit, provide stable identifiers and textual definitions, and evolve the vocabulary iteratively. OWL's open-world semantics make missing facts unknown rather than false. See [Ontology Development 101](https://protege.stanford.edu/publications/ontology_development/ontology101-noy-mcguinness.html), [W3C OWL 2 Primer](https://www.w3.org/TR/owl2-primer/), [W3C PROV-O](https://www.w3.org/TR/prov-o/), and [W3C Data on the Web Best Practices](https://www.w3.org/TR/dwbp/).

## Considered, not imported

- **Dublin Core Terms** is an RDF metadata vocabulary, but it does not define the census model; descriptive labels and values can stay local until a real interoperability need appears. Source documents are outside this binary-only first pass.
- **SPDX** is a genuine ontology for software supply-chain data, but package and build relationships are not represented in this census ontology.
- **KDM** is an OMG metamodel, not an OWL/RDF ontology. It is not used for grounding here.
- **SARIF** is a diagnostic interchange standard, and **CWE/CAPEC** are classification catalogs. No mapping to them is made here; they do not define the ordinary extraction outcomes represented by this census ontology.
- **UCO** is a cybersecurity ontology; **FnO** models abstract functions and implementations; **P-Plan** models planned workflows; **SWO** is oriented toward software in biomedical research. None is required for this census graph.
- The surveyed static-analysis/formal-methods candidates did not offer a mature, normative, cross-language ontology for native function identity, symbolic states, SMT outcomes, or proof obligations. Keep those out of this census ontology until concrete interoperability requirements and a sound fit are established.

## Review record

The previous interpreter-specific version completed three read-only review rounds. The generic binary model, inventory-generation provenance, and Bazel/Nix build-lineage extension have each been accepted by two read-only reviewers. Findings are recorded in [review log](review-log.md). No extraction, build, or test was run.
