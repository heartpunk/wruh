"""Deterministic fresh extraction of one provider-selected rooted function."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import capstone
import z3
from ayxg.expr import Declaration, TermSort

from extractor.amd64_state import (
    InstructionOutcomeFamily,
    canonical_declarations,
    step_instruction_outcomes,
)
from extractor.architecture import ArchitectureLayout, architecture_layout
from extractor.artifact import (
    DecodedInstructionEvidence,
    EdgeId,
    LocalEdge,
    Occurrence,
    OutcomeId,
    StaticOccurrenceId,
)
from extractor.binary_inventory import PinnedBinary
from extractor.cfg_blocks import (
    CfgBlockValidationError,
    ordered_instruction_records,
)
from extractor.typed_z3 import step_summary_from_z3


class FreshExtractionError(RuntimeError):
    """The exact rooted function cannot be freshly extracted."""


@dataclass(frozen=True)
class ExtractionCoverage:
    """Immutable traversal evidence; no status claims general closure."""

    unresolved_indirect_sites: tuple[int, ...]

    def to_data(self) -> dict[str, Any]:
        return {
            "scope": "intraprocedural-jumps-only",
            "status": "partial-indirect" if self.unresolved_indirect_sites else "direct-cfg",
            "unresolved_indirect_sites": list(self.unresolved_indirect_sites),
            "discovery": "loaded-table-seeds-do-not-bound-symbolic-targets",
        }

    @classmethod
    def from_data(cls, value: dict[str, Any]) -> ExtractionCoverage:
        if not isinstance(value, dict):
            raise FreshExtractionError("invalid extraction coverage")
        sites = value.get("unresolved_indirect_sites")
        if (not isinstance(sites, list)
                or any(type(site) is not int or site < 0 for site in sites)
                or sites != sorted(set(sites))):
            raise FreshExtractionError("invalid unresolved indirect sites")
        result = cls(tuple(sites))
        if value != result.to_data():
            raise FreshExtractionError("contradictory extraction coverage")
        return result


@dataclass(frozen=True)
class FreshFunction:
    function_id: str
    entry: int
    declarations: tuple[Declaration, ...]
    occurrences: tuple[Occurrence, ...]
    local_edges: tuple[LocalEdge, ...]
    architecture: ArchitectureLayout | None = None
    extraction_coverage: ExtractionCoverage | None = None

    schema = "ghot-fresh-function-v1"

    def to_data(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "function_id": self.function_id,
            "entry": self.entry,
            "declarations": [item.to_data() for item in self.declarations],
            "occurrences": [item.to_data() for item in self.occurrences],
            "local_edges": [item.to_data() for item in self.local_edges],
            **({"extraction_coverage": self.extraction_coverage.to_data()} if self.extraction_coverage is not None else {}),
            **({"architecture": self.architecture.to_data()} if self.architecture is not None else {}),
        }

    @classmethod
    def from_data(cls, value: dict[str, Any]) -> FreshFunction:
        if value.get("schema") != cls.schema:
            raise FreshExtractionError("unknown fresh function schema")
        result = cls(
            value["function_id"], value["entry"],
            tuple(Declaration.from_data(item) for item in value["declarations"]),
            tuple(Occurrence.from_data(item) for item in value["occurrences"]),
            tuple(LocalEdge.from_data(item) for item in value["local_edges"]),
            ArchitectureLayout.from_data(value["architecture"]) if "architecture" in value else None,
            ExtractionCoverage.from_data(value["extraction_coverage"]) if "extraction_coverage" in value else None,
        )
        if result.extraction_coverage is not None:
            symbolic_sources = {edge.source for edge in result.local_edges
                                if edge.summary.target.kind == "symbolic"}
            decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
            decoder.detail = True
            expected = []
            for item in result.occurrences:
                if (not isinstance(item.origin, DecodedInstructionEvidence)
                        or item.origin.canonical_address not in symbolic_sources):
                    continue
                raw = bytes.fromhex(item.origin.instruction_bytes)
                decoded = list(decoder.disasm(raw, item.origin.canonical_address))
                if len(decoded) != 1 or decoded[0].size != len(raw):
                    raise FreshExtractionError("invalid decoded symbolic transfer evidence")
                if decoded[0].group(capstone.CS_GRP_JUMP):
                    expected.append(item.origin.canonical_address)
            expected = sorted(set(expected))
            if list(result.extraction_coverage.unresolved_indirect_sites) != expected:
                raise FreshExtractionError("coverage sites disagree with symbolic jump occurrences")
        return result

    def canonical_json(self) -> bytes:
        return json.dumps(
            self.to_data(),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")


def artifact_declarations(arch: Any | None = None) -> tuple[Declaration, ...]:
    result = []
    for declaration in canonical_declarations(arch):
        if declaration.sort == "bv":
            sort = TermSort.bv(declaration.width)
        elif declaration.sort == "array":
            if declaration.index_width is None:
                raise FreshExtractionError(
                    f"array declaration {declaration.name!r} has no index width"
                )
            sort = TermSort.array(
                declaration.index_width,
                declaration.width,
            )
        else:
            raise FreshExtractionError(
                f"unknown canonical sort {declaration.sort!r}"
            )
        result.append(Declaration(declaration.name, sort))
    return tuple(result)


def _decoded_owners(cfg: dict[str, Any]) -> dict[int, tuple[str, ...]]:
    owners: dict[int, set[str]] = {}
    for function_id, root in cfg["roots"].items():
        for block in root["blocks"]:
            for instruction in block["instructions"]:
                owners.setdefault(instruction["address"], set()).add(
                    function_id
                )
    return {
        address: tuple(sorted(names))
        for address, names in owners.items()
    }


def occurrence_catalog(
    pinned: PinnedBinary,
    cfg: dict[str, Any],
) -> dict[int, StaticOccurrenceId]:
    """Assign one global ID to every decoded or primitive source address."""

    sources = set(_decoded_owners(cfg))
    primitive_sources = set(
        pinned.manifest["primitive_boundaries"].values()
    )
    overlap = sources & primitive_sources
    if overlap:
        raise FreshExtractionError(
            "decoded and primitive occurrence sources overlap: "
            f"{sorted(hex(address) for address in overlap)}"
        )
    return {
        address: StaticOccurrenceId(index)
        for index, address in enumerate(sorted(sources | primitive_sources))
    }


def _instruction_records(root: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    try:
        return ordered_instruction_records(root["blocks"])
    except CfgBlockValidationError as error:
        raise FreshExtractionError(str(error)) from error


def _local_edges(
    declarations: tuple[Declaration, ...],
    occurrence_id: StaticOccurrenceId,
    family: InstructionOutcomeFamily,
) -> tuple[LocalEdge, ...]:
    result = []
    for outcome in family.outcomes:
        guard = z3.And(family.source_guard, outcome.guard)
        target: int | z3.BitVecRef | str = (
            outcome.target_value
            if outcome.target_value is not None
            else outcome.target
        )
        is_fault = outcome.jumpkind in {
            "Ijk_SigFPE_IntDiv",
            "Ijk_SigTRAP",
            "Ijk_SigILL",
        }
        if is_fault:
            target = "error"
        fault_kind = outcome.fault_kind
        if is_fault and fault_kind is None:
            if outcome.jumpkind == "Ijk_SigFPE_IntDiv":
                fault_kind = "integer_division"
            elif outcome.jumpkind == "Ijk_SigILL":
                fault_kind = "invalid_opcode"
            else:
                fault_kind = "signal_trap"
        result.append(
            LocalEdge(
                id=EdgeId(
                    occurrence_id,
                    OutcomeId(outcome.outcome_id),
                ),
                source=family.source,
                summary=step_summary_from_z3(
                    declarations,
                    guard=guard,
                    updates=outcome.updates,
                    target=target,
                    mirrored_pc=outcome.target,
                ),
                jumpkind=outcome.jumpkind if is_fault else None,
                fault_kind=fault_kind if is_fault else None,
            )
        )
    return tuple(result)


def extract_fresh_function(
    pinned: PinnedBinary,
    cfg: dict[str, Any],
    function_id: str,
) -> FreshFunction:
    roots = cfg.get("roots")
    if not isinstance(roots, dict) or function_id not in roots:
        raise FreshExtractionError(f"unknown rooted function {function_id!r}")
    if cfg.get("image_sha256") != pinned.manifest.get("image_sha256"):
        raise FreshExtractionError("CFG and loaded image identities disagree")

    root = roots[function_id]
    declarations = artifact_declarations(pinned.project.arch)
    owners = _decoded_owners(cfg)
    catalog = occurrence_catalog(pinned, cfg)
    occurrences = []
    edges = []
    for instruction in _instruction_records(root):
        address = instruction["address"]
        occurrence_id = catalog[address]
        occurrences.append(
            Occurrence(
                occurrence_id,
                DecodedInstructionEvidence(
                    image_sha256=root.get("image_sha256", cfg["image_sha256"]),
                    canonical_address=address,
                    instruction_bytes=instruction["bytes"],
                    architecture="AMD64",
                    decode_mode="long64",
                    instruction_identity=(
                        f"{instruction['mnemonic']} {instruction['op_str']}"
                    ).strip(),
                    function_owners=owners[address],
                ),
            )
        )
        edges.extend(
            _local_edges(
                declarations,
                occurrence_id,
                step_instruction_outcomes(pinned.project, address),
            )
        )

    edges.sort(
        key=lambda edge: (
            edge.id.occurrence.value,
            edge.id.outcome.value,
        )
    )
    return FreshFunction(
        function_id=function_id,
        entry=root["address"],
        declarations=declarations,
        occurrences=tuple(occurrences),
        local_edges=tuple(edges),
        architecture=architecture_layout(pinned.project.arch),
        extraction_coverage=ExtractionCoverage.from_data(root["extraction_coverage"]) if "extraction_coverage" in root else None,
    )
