"""Protocol and values for ABI providers consumed by Wruh applications.

Target-specific authority, root naming, ABI relations, and external-call
models stay in the provider's owning project.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from extractor.artifact import LocalEdge
from extractor.binary_inventory import InventoryPolicy, PinnedBinary


class AbiProvider(Protocol):
    """Supplies target facts; callers inject it, core never discovers it."""

    @property
    def provider_id(self) -> str: ...

    def inventory_policy(self) -> InventoryPolicy: ...

    def external_call_edges(
        self, pinned: PinnedBinary, cfg: Mapping[str, Any]
    ) -> tuple[LocalEdge, ...]: ...
