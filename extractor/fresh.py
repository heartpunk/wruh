"""Fresh instruction extraction over selected decoded sites."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
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
from extractor.typed_z3 import step_summary_from_z3


class FreshExtractionError(RuntimeError):
    """The selected sites cannot be freshly extracted."""


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
            "Ijk_SigILL",
            "Ijk_SigTRAP",
        }
        if is_fault:
            target = "error"
        fault_kind = outcome.fault_kind
        if is_fault and fault_kind is None:
            fault_kind = {
                "Ijk_SigFPE_IntDiv": "integer_division",
                "Ijk_SigILL": "invalid_opcode",
                "Ijk_SigTRAP": "signal_trap",
            }[outcome.jumpkind]
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


@dataclass(frozen=True)
class FreshInstructions:
    declarations: tuple[Declaration, ...]
    occurrences: tuple[Occurrence, ...]
    local_edges: tuple[LocalEdge, ...]
    architecture: ArchitectureLayout

    schema = "wruh-fresh-instructions-v1"

    def to_data(self) -> dict[str, Any]:
        return {"schema": self.schema,
                "declarations": [item.to_data() for item in self.declarations],
                "occurrences": [item.to_data() for item in self.occurrences],
                "local_edges": [item.to_data() for item in self.local_edges],
                "architecture": self.architecture.to_data()}

    @classmethod
    def from_data(cls, value: dict[str, Any]) -> FreshInstructions:
        if value.get("schema") != cls.schema:
            raise FreshExtractionError("unknown fresh instruction schema")
        return cls(tuple(Declaration.from_data(item) for item in value["declarations"]),
                   tuple(Occurrence.from_data(item) for item in value["occurrences"]),
                   tuple(LocalEdge.from_data(item) for item in value["local_edges"]),
                   ArchitectureLayout.from_data(value["architecture"]))

    def canonical_json(self) -> bytes:
        return json.dumps(self.to_data(), ensure_ascii=False, allow_nan=False,
                          sort_keys=True, separators=(",", ":")).encode("utf-8")

def linear_site_records(project: Any, inventory: Any, *, chunk_size: int, seed: int, image_digest: str | None = None) -> tuple[tuple[int, Occurrence], ...]:
    """Assign site IDs from addresses before shuffling decoded work."""
    from extractor.instruction_inventory import shuffled_chunks

    digests: dict[str, str] = {}
    records = []
    for chunk in shuffled_chunks(inventory, chunk_size, seed):
        for instruction in chunk:
            obj = project.loader.find_object_containing(instruction.address)
            path = getattr(obj, "binary", None) if obj is not None else None
            if path and Path(path).is_file():
                path = str(path)
                if path not in digests:
                    digests[path] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
                digest = digests[path]
            elif image_digest is not None:
                digest = image_digest
            else:
                raise FreshExtractionError(f"no object for site {instruction.address:#x}")
            mapped_base = instruction.mapped_base
            if mapped_base is None:
                mapped_base = getattr(obj, "mapped_base", None) if obj is not None else None
            if mapped_base is None:
                raise FreshExtractionError(f"no mapping base for site {instruction.address:#x}")
            occurrence = Occurrence(
                StaticOccurrenceId(instruction.address),
                DecodedInstructionEvidence(
                    image_sha256=digest, canonical_address=instruction.address,
                    instruction_bytes=instruction.data.hex(), architecture="AMD64",
                    decode_mode="long64",
                    instruction_identity=f"{instruction.mnemonic} {instruction.operands}".strip(),
                    object_offset=instruction.address - mapped_base,
                    mapped_base=mapped_base,
                ),
            )
            records.append((instruction.address, occurrence))
    return tuple(records)


def extract_linear(project: Any, records: tuple[tuple[int, Occurrence], ...]) -> FreshInstructions:
    """Step each selected site from a fresh symbolic state."""
    declarations = artifact_declarations(project.arch)
    edges = []
    for address, occurrence in records:
        edges.extend(_local_edges(declarations, occurrence.id, step_instruction_outcomes(project, address)))
    edges.sort(key=lambda edge: (edge.id.occurrence.value, edge.id.outcome.value))
    occurrences = tuple(sorted((occurrence for _, occurrence in records), key=lambda item: item.id.value))
    return FreshInstructions(declarations, occurrences, tuple(edges), architecture_layout(project.arch))
