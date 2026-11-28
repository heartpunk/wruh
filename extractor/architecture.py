"""Register-file layout derived from the instantiated angr architecture.

Backing storage is declared once. Aliases are views, not independent state.
AMD64's four lazy condition-code fields are normalized to six flag bits by the
adapter; all other modeled registers, including artificial ones, are retained.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RegisterStorage:
    name: str
    offset: int
    size_bytes: int

    @property
    def bits(self) -> int:
        return self.size_bytes * 8


@dataclass(frozen=True)
class RegisterView:
    name: str
    storage_name: str
    byte_offset: int
    size_bytes: int


@dataclass(frozen=True)
class ArchitectureLayout:
    name: str
    storage: tuple[RegisterStorage, ...]
    views: tuple[RegisterView, ...]
    ip_view: str
    sp_view: str
    address_bits: int
    register_endness: str
    memory_endness: str

    @classmethod
    def from_data(cls, value: dict[str, Any]) -> ArchitectureLayout:
        return cls(value["name"], tuple(RegisterStorage(**item) for item in value["storage"]),
                   tuple(RegisterView(**item) for item in value["views"]),
                   value["ip_view"], value["sp_view"], value["address_bits"],
                   value["register_endness"], value["memory_endness"])

    def register(self, name: str) -> RegisterStorage:
        return next(item for item in self.storage if item.name == name)

    def view(self, name: str) -> RegisterView:
        return next(item for item in self.views if item.name == name)

    def to_data(self) -> dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)


# This is a semantic representation policy, not a register inventory. These
# fields encode a delayed calculation of the same six architectural flag bits.
NORMALIZED_AMD64_FLAGS = frozenset(("cc_op", "cc_dep1", "cc_dep2", "cc_ndep"))
