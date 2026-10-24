"""Address-indexed helpers for CFGs with overlapping instruction streams."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable, Mapping


class CfgBlockValidationError(ValueError):
    """A static CFG block or its instruction evidence is inconsistent."""


def instruction_index(
    blocks: Iterable[Mapping[str, Any]],
) -> dict[int, dict[str, Any]]:
    """Index decoded instructions by start address, sharing identical records."""

    records: dict[int, dict[str, Any]] = {}
    for block in blocks:
        for instruction in block["instructions"]:
            address = instruction["address"]
            previous = records.get(address)
            if previous is not None and previous != instruction:
                raise CfgBlockValidationError(
                    f"conflicting instruction decode at {address:#x}"
                )
            records[address] = instruction
    return records


def ordered_instruction_records(
    blocks: Iterable[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    records = instruction_index(blocks)
    return tuple(records[address] for address in sorted(records))


def successor_index(
    blocks: Iterable[Mapping[str, Any]],
) -> dict[int, tuple[int, ...]]:
    """Union CFG successors for each instruction address across its blocks."""

    successors: dict[int, set[int]] = defaultdict(set)
    for block in blocks:
        for instruction in block["instructions"]:
            address = instruction["address"]
            successors[address].update(block["successors"])
    return {
        address: tuple(sorted(targets))
        for address, targets in successors.items()
    }


def validate_block_partition(
    *,
    root_name: str,
    entry: int,
    extent_end: int,
    blocks: list[dict[str, Any]],
) -> None:
    """Validate rooted CFG records without requiring disjoint byte ranges."""

    if not blocks or blocks[0]["address"] != entry:
        raise CfgBlockValidationError(f"{root_name}: CFG omits the entry block")

    addresses = [block["address"] for block in blocks]
    if len(addresses) != len(set(addresses)):
        raise CfgBlockValidationError(
            f"{root_name}: duplicate static block address"
        )
    address_set = set(addresses)
    instruction_index(blocks)

    for block in blocks:
        block_start = block["address"]
        block_end = block_start + block["size"]
        if (
            block["size"] <= 0
            or block_start < entry
            or block_end > extent_end
        ):
            raise CfgBlockValidationError(
                f"{root_name}: block [{block_start:#x}, {block_end:#x}) "
                f"leaves [{entry:#x}, {extent_end:#x})"
            )
        records = block["instructions"]
        if not records or records[0]["address"] != block_start:
            raise CfgBlockValidationError(
                f"{root_name}: block {block_start:#x} has no entry instruction"
            )
        cursor = block_start
        for instruction in records:
            if instruction["address"] != cursor or instruction["size"] <= 0:
                raise CfgBlockValidationError(
                    f"{root_name}: noncontiguous instruction roster in "
                    f"block {block_start:#x}"
                )
            cursor += instruction["size"]
        if cursor != block_end:
            raise CfgBlockValidationError(
                f"{root_name}: instruction roster does not cover "
                f"block {block_start:#x}"
            )
        unknown = set(block["successors"]) - address_set
        if unknown:
            raise CfgBlockValidationError(
                f"{root_name}: local successors are not block entries: "
                f"{sorted(hex(address) for address in unknown)}"
            )
