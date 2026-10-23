# Ontology landscape for generic binary function extraction

Reviewed 2026-10-23. This is a research landscape, not the selected ontology design. It distinguishes actual ontologies from vocabularies, metamodels, exchange standards, and classification catalogs. The adopted first pass imports only PROV-O; the generic binary model and its interpreter specialization are described in [the ontology proposal](../ontology/README.md).

## Candidate ontologies and vocabularies

### Provenance: PROV-O

[PROV-O](https://www.w3.org/TR/prov-o/) is the strongest core anchor. It is a W3C Recommendation and an OWL 2 ontology that explicitly supports specialization for domain-specific provenance. Its `Entity`, `Activity`, and `Agent` concepts fit the distinction between fixed inputs/results, time-bounded build/inventory/extraction events, and responsible people or software. Its `used`, `wasGeneratedBy`, `wasDerivedFrom`, `wasAssociatedWith`, `wasInformedBy`, and start/end-time relations describe lineage and retries; `Collection` and `hadMember` cover grouped inventories or outputs. Qualified usage and association relations can express roles when the simple relations are insufficient.

Do not substitute `dcterms:provenance` for this event graph. DCMI defines that term as a statement about significant changes in ownership or custody that affect authenticity, integrity, and interpretation. The [PROV-DC mapping](https://www.w3.org/TR/prov-dc/) is explicitly partial and is a W3C Working Group Note, so it is a useful crosswalk rather than a binding mapping.

### Descriptive metadata: Dublin Core Terms and Schema.org

[DCMI Metadata Terms](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/) is a current DCMI Recommendation intended to be combined with compatible vocabularies. Its terms such as `identifier`, `created`, `modified`, `source`, `format`, `extent`, `type`, and `conformsTo` describe resources, versions, formats, and standards without pretending to define program-analysis semantics. The DCMI Type Vocabulary includes `Software`, `Dataset`, and `Collection`; these are broad descriptions, not detailed models of binary images or function inventories. Prefer the DCMI `/terms/` namespace for its current terms.

[Schema.org](https://schema.org/SoftwareApplication) is a broad, widely used vocabulary for high-level software description. `SoftwareApplication` includes version, platform, operating-system, and requirements properties; [`SoftwareSourceCode`](https://schema.org/SoftwareSourceCode) describes source repositories and languages. It complements DCMI, but neither vocabulary defines symbol identity, binary address regions, control-flow edges, or solver semantics.

### Software identity and supply-chain concepts: SPDX

[SPDX 3.0.1](https://spdx.github.io/spdx-spec/v3.0.1/) is a strong formal vocabulary for identifying interpreter packages, files, artifacts, hashes, build inputs/outputs, tools, and hosts. Its specification publishes an OWL ontology, and its Build profile describes software build activities and their inputs, outputs, tools, and host. SPDX is best used for the identity and relationships of the exact runtime distribution and its built artifacts. It does not provide the extractor's internal function, basic-block, or symbolic-state ontology.

### Program structure: OMG KDM as a crosswalk

[OMG KDM 1.4](https://www.omg.org/spec/KDM/) is the closest established vocabulary for the structural program model, but it is an OMG metamodel rather than an OWL/RDF ontology. Its source, code, and action packages include executable/library files, `BinaryRegion`, callable units, action/block units, control-flow, calls, dispatches, and read/write relations. This makes it a useful semantic crosswalk for binaries, function owners, CFG nodes, and transfers.

KDM's address semantics need care: `BinaryRegion` uses offsets into a byte sequence beginning at zero. Those offsets must not be conflated with ELF virtual addresses, load addresses, or relocation addresses. KDM also does not cover decoded machine instructions, instruction-set details, symbolic states, path constraints, SMT queries/verdicts, or extraction failure/completeness. The proposed target needs precise domain terms for those distinctions.

### Plans and functions: optional, narrow alignments

[P-Plan](https://www.opmw.org/model/p-plan/) extends PROV-O with planned steps and variables linked to execution. It is useful if the model includes a prospective extraction plan as well as the observed run; otherwise PROV-O's `Plan` and run provenance may be enough. P-Plan is an OWL ontology, but not a W3C Recommendation.

The [Function Ontology (FnO)](https://fno.io/spec/20230512/) distinguishes an abstract function from an implementation, mapping, or execution. It could describe a semantic function contract or the relation between a source-level operation and an implementation. It is not a model for native binary function identity, address extent, symbol aliases, CFGs, or extraction success. Its published specification identifies itself as an unofficial draft, so it should remain optional.

The OBO [Software Ontology (SWO)](https://github.com/allysonlister/swo) covers software tools, types, tasks, versions, licenses, provenance, and related data, with a biomedical-software emphasis and ad hoc releases. It can provide a useful term for an analysis tool when the term matches, but not for the analyzed runtime's internal code graph. Do not confuse it with SEON's distinct `SwO`: the [SEON network](https://dev.nemo.inf.ufes.br/seon/menu.html) models software-engineering concepts such as processes, activities, artifacts, resources, and stakeholders, but its published version is old. Treat both as optional mappings rather than foundational dependencies.

## Security and analysis vocabularies

### Security

The [Unified Cyber Ontology (UCO)](https://unifiedcyberontology.org/) is a genuine community-developed cybersecurity ontology/model. It is relevant if a future result represents forensic, threat-intelligence, malware, or vulnerability-analysis observations; it is not a general taxonomy for extraction outcomes or resource failures.

[CWE](https://cwe.mitre.org/) and [CAPEC](https://capec.mitre.org/) are authoritative, versioned weakness and attack-pattern classifications, not general-purpose ontologies. Link a CWE identifier only when asserting an actual weakness/root cause; link CAPEC only when describing an actual attack pattern. Neither is suitable for labeling CFG, solver, timeout, or exporter failures. MITRE's current CWE downloads list 4.20 and announce the breaking 5.0/schema 8.0 release for 2026-10-28, so any use should pin the edition and preserve the classification version. [STIX 2.1](https://docs.oasis-open.org/cti/stix/v2.1/os/stix-v2.1-os.html) is a cyber-threat-intelligence exchange standard, not a general software ontology.

### Static analysis and formal methods

[CodeOntology](https://codeontology.org/doc) is an OWL 2 research ontology for object-oriented source code, focused primarily on Java. It demonstrates useful source-level terms such as methods, statements, expressions, and invocations, but it does not provide a cross-language native-binary, CFG, or symbolic-execution vocabulary. Program-analysis efforts such as [PATO](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ECOOP.2016.26) are useful research precedents, not broadly governed standards.

[PML 3.0](https://dvcs.w3.org/hg/prov/raw-file/default/ontology/working-dir/pml-3/Overview.html) is an OWL proof/provenance ontology that extends PROV-O and describes justifications and inference steps. Its publication is a historical Working Draft, so it is not a strong current foundation for formal-methods results. I found no mature, normative, cross-language ontology for symbolic execution, SMT solving, machine-code verification, or the status of proof obligations. PROV-O can ground the provenance of an analysis activity and its evidence; exact state, query, verdict, and witness semantics need a domain vocabulary.

[SARIF 2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/sarif-v2.1.0-os.html) is an OASIS Standard for exchanging static-analysis findings, not an ontology. It can be useful for genuine rule-based diagnostics, but a SARIF result is a finding; it is not a per-function census concept. Do not equate an extraction attempt's blocked/incomplete state with a security finding.

## Crosswalk by extractor concept

| Concept area | Best existing grounding | Boundary to preserve |
| --- | --- | --- |
| Source, interpreter distribution, build, and binary lineage | PROV-O + DCMI; SPDX for package/file/build identity; Schema.org for broad software description | These describe artifacts and their provenance, not machine-code semantics. |
| Inventory and output groupings | PROV-O `Collection`; DCMI `Dataset`/`Collection` for broad descriptive type | The candidate unit, alias rule, extent rule, and census denominator have no precise standard ontology term. |
| Binary regions, functions, blocks, and control transfers | KDM as a semantic crosswalk; CodeOntology only for source-level code concepts | Preserve byte-offset versus virtual-address meanings. Native instructions and CFG specifics need explicit domain concepts. |
| Extraction and analysis runs | PROV-O; optionally P-Plan for intended steps versus observed execution | Detailed attempt status, failure stage, retry semantics, and completeness are not supplied by the core ontologies. |
| Symbolic execution, solver, proof, and verification evidence | PROV-O for activity/evidence lineage; PML only as a historical reference | No current, normative, general ontology was found for interpreter-level symbolic states, SMT outcomes, or extraction proof obligations. |
| Security claim | UCO for cyber-investigation concepts; CWE for actual weakness; CAPEC for actual attack pattern | Do not apply security classifications to ordinary extraction failures. |

## Selection for the first pass

Import **PROV-O only**. It is an OWL 2 ontology and W3C Recommendation designed for provenance interchange and explicitly supports domain-specific specialization. Its Entity/Activity/Agent model fits the provenance spine for analyzed binary images and outputs, inventory-generation/census/attempt events, and responsible software agents. The local ontology adds only extraction-specific meanings where PROV-O has no exact term; interpreter targets are one specialization of the generic binary model.

DCMI Terms and Schema.org are descriptive vocabularies rather than the ontology needed for census structure. SPDX is a genuine ontology but its software supply-chain profile is not needed to represent current census facts. KDM is an OMG metamodel, not an ontology. SARIF is an interchange standard; CWE/CAPEC are classifications. The other actual ontologies surveyed do not offer sufficiently exact terms for this first-pass domain, so they remain unimported. Do not map native function identity, address-space meaning, extraction disposition, symbolic execution, SMT results, or unresolved boundaries to approximate external terms.

The model follows the ontology-development guidance to state scope and competency questions, reuse exact terms, document terms with definitions, iterate, and avoid using OWL axioms as a closed-world completeness validator. Current OWL open-world semantics mean absence of an assertion is unknown, not false or zero; completeness/count reconciliation remains a dataset-level concern. References: [Ontology Development 101](https://protege.stanford.edu/publications/ontology_development/ontology101-noy-mcguinness.html), [W3C OWL 2 Primer](https://www.w3.org/TR/owl2-primer/), [W3C PROV-O](https://www.w3.org/TR/prov-o/), and [W3C Data on the Web Best Practices](https://www.w3.org/TR/dwbp/).
