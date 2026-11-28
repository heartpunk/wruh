"""Fresh instruction extraction over selected decoded sites."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ayxg.expr import Declaration, TypedExpr
from equanimity import StepResult

from extractor.architecture import ArchitectureLayout
from extractor.artifact import (
    Assignment,
    DecodedInstructionEvidence,
    EdgeId,
    LocalEdge,
    Occurrence,
    OutcomeId,
    StaticOccurrenceId,
    StepSummary,
    Target,
)
from extractor.backend import Session
from extractor.instruction_inventory import Inventory, shuffled_chunks


class FreshExtractionError(RuntimeError):
    """The selected sites cannot be freshly extracted."""


def _local_edges(
    declarations: tuple[Declaration, ...],
    occurrence_id: StaticOccurrenceId,
    family: StepResult,
) -> tuple[LocalEdge, ...]:
    fault_kinds = {
        "Ijk_SigFPE_IntDiv": "integer_division",
        "Ijk_SigILL": "invalid_opcode",
        "Ijk_SigTRAP": "signal_trap",
    }
    result = []
    for outcome in family.outcomes:
        fault = fault_kinds.get(outcome.jumpkind)
        if fault is not None:
            target = Target("error")
        elif outcome.target_value is None:
            target = Target("symbolic", outcome.target)
        else:
            target = Target("address", outcome.target_value)
        summary = StepSummary(
            guard=TypedExpr.conjoin(family.source_guard, outcome.guard),
            simultaneous_update=tuple(Assignment(d.name, outcome.updates[d.name]) for d in declarations),
            target=target, mirrored_pc=outcome.target,
        )
        summary.validate(declarations)
        result.append(LocalEdge(
            id=EdgeId(occurrence_id, OutcomeId(outcome.outcome_id)), source=family.address,
            summary=summary, jumpkind=outcome.jumpkind if fault is not None else None,
            fault_kind=(outcome.fault_kind or fault) if fault is not None else None,
        ))
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

def linear_site_records(inventory: Inventory, *, chunk_size: int, seed: int) -> tuple[tuple[int, Occurrence], ...]:
    """Assign site IDs from addresses before shuffling decoded work."""
    records = []
    for chunk in shuffled_chunks(inventory, chunk_size, seed):
        for instruction in chunk:
            digest, offset, mode = instruction.site_key
            occurrence = Occurrence(
                StaticOccurrenceId(instruction.address),
                DecodedInstructionEvidence(
                    image_sha256=digest, canonical_address=instruction.address,
                    instruction_bytes=instruction.data.hex(), architecture="AMD64",
                    decode_mode=mode,
                    instruction_identity=f"{instruction.mnemonic} {instruction.operands}".strip(),
                    object_offset=offset,
                    mapped_base=instruction.mapped_base,
                ),
            )
            records.append((instruction.address, occurrence))
    return tuple(records)


def extract_linear(session: Session, records: tuple[tuple[int, Occurrence], ...]) -> FreshInstructions:
    """Step each selected site from a fresh symbolic state."""
    declarations = session.image.declarations
    edges = []
    for address, occurrence in records:
        edges.extend(_local_edges(declarations, occurrence.id, session.step(address)))
    edges.sort(key=lambda edge: (edge.id.occurrence.value, edge.id.outcome.value))
    occurrences = tuple(sorted((occurrence for _, occurrence in records), key=lambda item: item.id.value))
    return FreshInstructions(declarations, occurrences, tuple(edges), ArchitectureLayout.from_data(session.image.architecture))
