"""Deterministic fresh extraction of one provider-selected rooted function."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

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
from extractor.typed_z3 import step_summary_from_z3


class FreshExtractionError(RuntimeError):
    """The exact rooted function cannot be freshly extracted."""


@dataclass(frozen=True)
class FreshFunction:
    function_id: str
    entry: int
    declarations: tuple[Declaration, ...]
    occurrences: tuple[Occurrence, ...]
    local_edges: tuple[LocalEdge, ...]
    architecture: ArchitectureLayout | None = None

    schema = "ghot-fresh-function-v1"

    def to_data(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "function_id": self.function_id,
            "entry": self.entry,
            "declarations": [item.to_data() for item in self.declarations],
            "occurrences": [item.to_data() for item in self.occurrences],
            "local_edges": [item.to_data() for item in self.local_edges],
            **({"architecture": self.architecture.to_data()} if self.architecture is not None else {}),
        }

    @classmethod
    def from_data(cls, value: dict[str, Any]) -> FreshFunction:
        if value.get("schema") != cls.schema:
            raise FreshExtractionError("unknown fresh function schema")
        return cls(
            value["function_id"], value["entry"],
            tuple(Declaration.from_data(item) for item in value["declarations"]),
            tuple(Occurrence.from_data(item) for item in value["occurrences"]),
            tuple(LocalEdge.from_data(item) for item in value["local_edges"]),
            ArchitectureLayout.from_data(value["architecture"]) if "architecture" in value else None,
        )

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
    records = tuple(
        instruction
        for block in root["blocks"]
        for instruction in block["instructions"]
    )
    addresses = tuple(record["address"] for record in records)
    if addresses != tuple(sorted(addresses)) or len(set(addresses)) != len(
        addresses
    ):
        raise FreshExtractionError(
            "root instructions are not unique and canonically ordered"
        )
    return records


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
        is_fault = outcome.jumpkind in {"Ijk_SigFPE_IntDiv", "Ijk_SigTRAP"}
        if is_fault:
            target = "error"
        fault_kind = outcome.fault_kind
        if is_fault and fault_kind is None:
            fault_kind = (
                "integer_division"
                if outcome.jumpkind == "Ijk_SigFPE_IntDiv"
                else "signal_trap"
            )
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
    )
