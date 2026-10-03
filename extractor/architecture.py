"""Register-file layout derived from the instantiated angr architecture.

Backing storage is declared once. Aliases are views, not independent state.
AMD64's four lazy condition-code fields are normalized to six flag bits by the
adapter; all other modeled registers, including artificial ones, are retained.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


class ArchitectureLayoutError(ValueError):
    pass


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


def architecture_layout(arch: Any) -> ArchitectureLayout:
    if arch.name != "AMD64" or arch.bits != 64:
        raise ArchitectureLayoutError(f"unsupported architecture {arch.name}/{arch.bits}")
    candidates = []
    for register in arch.register_list:
        if register.vex_offset is None:
            raise ArchitectureLayoutError(f"register {register.name} lacks a backing offset")
        offset, size = int(register.vex_offset), int(register.size)
        if offset < 0 or size <= 0:
            raise ArchitectureLayoutError(f"invalid storage for {register.name}")
        candidates.append(RegisterStorage(register.name, offset, size))
    # Largest region first at a shared start makes a super-register the owner.
    candidates.sort(key=lambda item: (item.offset, -item.size_bytes, item.name))
    storage: list[RegisterStorage] = []
    for item in candidates:
        covering = [s for s in storage if s.offset <= item.offset and
                    item.offset + item.size_bytes <= s.offset + s.size_bytes]
        if covering:
            continue
        if any(item.offset < s.offset + s.size_bytes and
               s.offset < item.offset + item.size_bytes for s in storage):
            raise ArchitectureLayoutError(f"partially overlapping register storage: {item.name}")
        storage.append(item)
    views = []
    for name, (offset, size) in sorted(arch.registers.items()):
        owners = [s for s in storage if s.offset <= offset and
                  offset + size <= s.offset + s.size_bytes]
        if len(owners) != 1:
            raise ArchitectureLayoutError(f"register view {name} has {len(owners)} owners")
        owner = owners[0]
        views.append(RegisterView(name, owner.name, offset - owner.offset, size))
    def control_name(offset: int) -> str:
        matches = [s for s in storage if s.offset == offset and s.bits == arch.bits]
        if len(matches) != 1:
            raise ArchitectureLayoutError(f"control offset {offset} has no unique full-width storage")
        return matches[0].name
    return ArchitectureLayout(arch.name, tuple(storage), tuple(views),
                              control_name(arch.ip_offset), control_name(arch.sp_offset),
                              arch.bits, str(arch.register_endness), str(arch.memory_endness))
