"""Protocol and values for ABI providers consumed by Wruh applications.

Target-specific authority, root naming, ABI relations, and external-call
models stay in the provider's owning project.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from extractor.artifact import LocalEdge, TypedExpr
from extractor.binary_inventory import InventoryPolicy, PinnedBinary


@dataclass(frozen=True)
class SourceEdge:
    """One authoritative source transition for a handler contract."""

    name: str
    guard: TypedExpr
    update: Mapping[str, TypedExpr]
    status: int


@dataclass(frozen=True)
class OutputProjection:
    """One named source-versus-machine result observation."""

    name: str
    source_value: TypedExpr | None
    machine_value: TypedExpr


@dataclass(frozen=True)
class HandlerContract:
    """Source semantics and ABI relation for one provider-named root."""

    root_id: str
    opcode: int
    abi_relation: TypedExpr
    source_edges: tuple[SourceEdge, ...]
    projections: tuple[OutputProjection, ...]


class AbiProvider(Protocol):
    """Supplies target facts; callers inject it, core never discovers it."""

    @property
    def provider_id(self) -> str: ...

    def inventory_policy(self) -> InventoryPolicy: ...

    def handler_contract(
        self, root_id: str, cfg: Mapping[str, Any]
    ) -> HandlerContract: ...

    def external_call_edges(
        self, pinned: PinnedBinary, cfg: Mapping[str, Any]
    ) -> tuple[LocalEdge, ...]: ...
