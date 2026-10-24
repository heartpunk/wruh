"""Strict static CFG inventory for a provider-selected artifact."""

from __future__ import annotations

from collections import Counter
from typing import Any

import capstone
import pyvex

from extractor.amd64_terminals import is_ud2_no_decode_terminal
from extractor.binary_inventory import (
    InventoryError,
    PinnedBinary,
)


def _instruction_records(
    pinned: PinnedBinary, block_address: int, block_size: int
) -> list[dict[str, Any]]:
    code = pinned.project.loader.memory.load(block_address, block_size)
    decoded = list(
        pinned.project.arch.capstone.disasm(code, block_address)
    )
    if (
        not decoded
        or decoded[0].address != block_address
        or decoded[-1].address + decoded[-1].size
        != block_address + block_size
    ):
        raise InventoryError(
            f"incomplete static block decode at {block_address:#x}"
        )
    return [
        {
            "address": instruction.address,
            "bytes": instruction.bytes.hex(),
            "mnemonic": instruction.mnemonic,
            "op_str": instruction.op_str,
            "size": instruction.size,
        }
        for instruction in decoded
    ]


def _validate_block_partition(
    *,
    root_name: str,
    entry: int,
    extent_end: int,
    blocks: list[dict[str, Any]],
) -> None:
    if not blocks or blocks[0]["address"] != entry:
        raise InventoryError(f"{root_name}: CFG omits the entry block")

    addresses = [block["address"] for block in blocks]
    if len(addresses) != len(set(addresses)):
        raise InventoryError(f"{root_name}: duplicate static block address")
    address_set = set(addresses)

    instruction_addresses: set[int] = set()
    previous_end = entry
    for block in blocks:
        block_start = block["address"]
        block_end = block_start + block["size"]
        if (
            block["size"] <= 0
            or block_start < entry
            or block_end > extent_end
        ):
            raise InventoryError(
                f"{root_name}: block [{block_start:#x}, {block_end:#x}) "
                f"leaves [{entry:#x}, {extent_end:#x})"
            )
        if block_start < previous_end:
            raise InventoryError(
                f"{root_name}: overlapping static block at {block_start:#x}"
            )
        previous_end = block_end
        records = block["instructions"]
        if not records or records[0]["address"] != block_start:
            raise InventoryError(
                f"{root_name}: block {block_start:#x} has no entry instruction"
            )
        cursor = block_start
        for instruction in records:
            if instruction["address"] != cursor or instruction["size"] <= 0:
                raise InventoryError(
                    f"{root_name}: noncontiguous instruction roster in "
                    f"block {block_start:#x}"
                )
            if instruction["address"] in instruction_addresses:
                raise InventoryError(
                    f"{root_name}: instruction {instruction['address']:#x} "
                    "belongs to multiple blocks"
                )
            instruction_addresses.add(instruction["address"])
            cursor += instruction["size"]
        if cursor != block_end:
            raise InventoryError(
                f"{root_name}: instruction roster does not cover "
                f"block {block_start:#x}"
            )
        unknown = set(block["successors"]) - address_set
        if unknown:
            raise InventoryError(
                f"{root_name}: local successors are not block entries: "
                f"{sorted(hex(address) for address in unknown)}"
            )


def _resolve_call_target(
    target: int,
    *,
    root_at_address: dict[int, str],
    primitive_at_address: dict[int, str],
) -> tuple[str, str]:
    if target in root_at_address:
        return ("direct-local", root_at_address[target])
    if target in primitive_at_address:
        return ("modeled-primitive", primitive_at_address[target])
    return ("open", "indirect" if target is None else f"address:{target:#x}")


def _constant_target(expression: Any) -> int | None:
    if hasattr(expression, "con") and hasattr(expression.con, "value"):
        return int(expression.con.value)
    if hasattr(expression, "value"):
        return int(expression.value)
    return None


def _recover_relative_jump_tables(
    pinned: PinnedBinary,
    *,
    root_name: str,
    root: dict[str, Any],
) -> dict[int, list[int]]:
    """Resolve only the pinned Rust relative-offset jump-table idiom."""

    entry = root["address"]
    extent_end = entry + root["size"]
    code = pinned.project.loader.memory.load(entry, root["size"])
    instructions = list(
        pinned.project.arch.capstone.disasm(code, entry)
    )
    if (
        not instructions
        or instructions[0].address != entry
        or instructions[-1].address + instructions[-1].size != extent_end
    ):
        raise InventoryError(
            f"{root_name}: incomplete linear decode before CFG recovery"
        )
    instruction_at = {
        instruction.address: index
        for index, instruction in enumerate(instructions)
    }
    expected_sites = {
        item["address"]
        for item in pinned.manifest.get("indirect_jumps", {}).get(
            root_name, []
        )
    }
    specs: list[tuple[int, int]] = []

    for site in sorted(expected_sites):
        index = instruction_at.get(site)
        if index is None or index < 3:
            raise InventoryError(
                f"{root_name}: pinned indirect jump {site:#x} has no "
                "decodable relative-table prelude"
            )
        lea, load, add, jump = instructions[index - 3 : index + 1]
        if (
            lea.mnemonic != "lea"
            or load.mnemonic != "movsxd"
            or add.mnemonic != "add"
            or not jump.mnemonic.startswith("jmp")
            or len(lea.operands) != 2
            or len(load.operands) != 2
            or len(add.operands) != 2
            or len(jump.operands) != 1
            or lea.operands[0].type != capstone.x86.X86_OP_REG
            or lea.operands[1].type != capstone.x86.X86_OP_MEM
            or load.operands[0].type != capstone.x86.X86_OP_REG
            or load.operands[1].type != capstone.x86.X86_OP_MEM
            or add.operands[0].type != capstone.x86.X86_OP_REG
            or add.operands[1].type != capstone.x86.X86_OP_REG
            or jump.operands[0].type != capstone.x86.X86_OP_REG
        ):
            raise InventoryError(
                f"{root_name}: unsupported indirect-jump prelude at {site:#x}"
            )

        base_register = lea.operands[0].reg
        target_register = jump.operands[0].reg
        lea_memory = lea.operands[1].mem
        load_memory = load.operands[1].mem
        if (
            lea_memory.base != capstone.x86.X86_REG_RIP
            or lea_memory.index != capstone.x86.X86_REG_INVALID
            or load.operands[0].reg != target_register
            or load_memory.base != base_register
            or load_memory.index == capstone.x86.X86_REG_INVALID
            or load_memory.scale != 4
            or load_memory.disp != 0
            or add.operands[0].reg != target_register
            or add.operands[1].reg != base_register
        ):
            raise InventoryError(
                f"{root_name}: unsupported relative jump table at {site:#x}"
            )
        table_base = lea.address + lea.size + lea_memory.disp
        specs.append((site, table_base))

    specs.sort(key=lambda spec: spec[1])
    if len({base for _, base in specs}) != len(specs):
        raise InventoryError(f"{root_name}: jump tables alias one base")

    instruction_addresses = set(instruction_at)
    result: dict[int, list[int]] = {}
    for spec_index, (site, table_base) in enumerate(specs):
        bounded_count: int | None = None
        if spec_index + 1 < len(specs):
            next_base = specs[spec_index + 1][1]
            distance = next_base - table_base
            if distance <= 0 or distance % 4 != 0:
                raise InventoryError(
                    f"{root_name}: adjacent jump-table bases are not "
                    "word-aligned"
                )
            bounded_count = distance // 4
        targets: list[int] = []
        terminated = False
        for item_index in range(
            bounded_count if bounded_count is not None else 256
        ):
            raw = pinned.project.loader.memory.load(
                table_base + item_index * 4, 4
            )
            offset = int.from_bytes(raw, byteorder="little", signed=True)
            target = table_base + offset
            valid = (
                entry <= target < extent_end
                and target in instruction_addresses
            )
            if not valid:
                if bounded_count is not None:
                    raise InventoryError(
                        f"{root_name}: invalid bounded jump-table target "
                        f"{target:#x} at {site:#x}"
                    )
                terminated = True
                break
            targets.append(target)
        if bounded_count is None and not terminated:
            raise InventoryError(
                f"{root_name}: unterminated jump table at {site:#x}"
            )
        if not targets or len(targets) != len(set(targets)):
            raise InventoryError(
                f"{root_name}: empty or duplicate jump table at {site:#x}"
            )
        result[site] = sorted(targets)
    return result


def _walk_function(
    pinned: PinnedBinary,
    *,
    root_name: str,
    root: dict[str, Any],
    jump_tables: dict[int, list[int]],
) -> tuple[list[dict[str, Any]], list[dict[str, int]], set[int]]:
    """BFS one symbol-fenced function using VEX static control flow."""

    entry = root["address"]
    extent_end = entry + root["size"]
    queue = [entry]
    seen: set[int] = set()
    blocks: list[dict[str, Any]] = []
    calls: list[dict[str, int]] = []
    walked_indirect_sites: set[int] = set()

    code = pinned.project.loader.memory.load(entry, root["size"])
    linear_instructions = list(
        pinned.project.arch.capstone.disasm(code, entry)
    )
    stop_points = {
        target
        for targets in jump_tables.values()
        for target in targets
    }
    stop_points.add(entry)
    for instruction in linear_instructions:
        fallthrough = instruction.address + instruction.size
        if instruction.mnemonic.startswith("call"):
            if entry <= fallthrough < extent_end:
                stop_points.add(fallthrough)
            continue
        if not instruction.mnemonic.startswith("j"):
            continue
        if (
            len(instruction.operands) == 1
            and instruction.operands[0].type
            == capstone.x86.X86_OP_IMM
            and entry <= instruction.operands[0].imm < extent_end
        ):
            stop_points.add(instruction.operands[0].imm)
        if (
            not instruction.mnemonic.startswith("jmp")
            and entry <= fallthrough < extent_end
        ):
            stop_points.add(fallthrough)

    while queue:
        block_address = queue.pop(0)
        if block_address in seen:
            continue
        seen.add(block_address)
        block = pinned.project.factory.block(
            block_address,
            extra_stop_points=stop_points,
        )
        if block.size <= 0 or block_address + block.size > extent_end:
            raise InventoryError(
                f"{root_name}: block at {block_address:#x} leaves its extent"
            )
        instructions = _instruction_records(
            pinned, block_address, block.size
        )
        imarks = tuple(
            statement.addr
            for statement in block.vex.statements
            if isinstance(statement, pyvex.stmt.IMark)
        )
        decoded_addresses = tuple(
            instruction["address"] for instruction in instructions
        )
        if imarks != decoded_addresses:
            raise InventoryError(
                f"{root_name}: VEX and Capstone instruction rosters "
                f"disagree at {block_address:#x}"
            )

        successors: set[int] = set()
        for statement in block.vex.statements:
            if not isinstance(statement, pyvex.stmt.Exit):
                continue
            if statement.jumpkind == "Ijk_SigFPE_IntDiv":
                continue  # Fault successors are terminal STS errors, not CFG nodes.
            target = _constant_target(statement.dst)
            if target is None:
                raise InventoryError(
                    f"{root_name}: symbolic conditional target at "
                    f"{block_address:#x}"
                )
            if entry <= target < extent_end:
                successors.add(target)
            elif not pinned.manifest.get("open_transfers"):
                raise InventoryError(f"{root_name}: conditional edge leaves function")

        jumpkind = block.vex.jumpkind
        if jumpkind == "Ijk_Ret":
            pass
        elif jumpkind == "Ijk_Call":
            target = _constant_target(block.vex.next)
            call_instruction = instructions[-1]
            if not call_instruction["mnemonic"].startswith("call"):
                raise InventoryError(
                    f"{root_name}: VEX call lacks a Capstone call at "
                    f"{block_address:#x}"
                )
            raw = pinned.project.loader.memory.load(
                call_instruction["address"], call_instruction["size"]
            )
            decoded = list(
                pinned.project.arch.capstone.disasm(
                    raw, call_instruction["address"]
                )
            )
            if (
                len(decoded) != 1
                or len(decoded[0].operands) != 1
                or (target is not None and (
                    decoded[0].operands[0].type != capstone.x86.X86_OP_IMM
                    or decoded[0].operands[0].imm != target))
            ):
                raise InventoryError(
                    f"{root_name}: encoded and VEX call targets disagree "
                    f"at {call_instruction['address']:#x}"
                )
            calls.append(
                {
                    "address": call_instruction["address"],
                    "block": block_address,
                    "target": target,
                }
            )
            fallthrough = block_address + block.size
            if not (entry <= fallthrough < extent_end):
                raise InventoryError(
                    f"{root_name}: call fallthrough leaves the function"
                )
            successors.add(fallthrough)
        elif jumpkind == "Ijk_Boring":
            target = _constant_target(block.vex.next)
            if target is not None:
                if not (entry <= target < extent_end):
                    if not pinned.manifest.get("open_transfers"):
                        raise InventoryError(f"{root_name}: non-call edge leaves function")
                else:
                    successors.add(target)
            else:
                site = instructions[-1]["address"]
                if site not in jump_tables and not pinned.manifest.get("open_transfers"):
                    raise InventoryError(
                        f"{root_name}: undeclared indirect jump at {site:#x}"
                    )
                if site in jump_tables:
                    walked_indirect_sites.add(site)
                    successors.update(jump_tables[site])
        elif is_ud2_no_decode_terminal(
            jumpkind,
            instructions,
            block_end=block_address + block.size,
            has_zero_length_imark=any(
                isinstance(statement, pyvex.stmt.IMark) and statement.len == 0
                for statement in block.vex.statements
            ),
        ):
            # x86 UD2 is an architecturally defined invalid-opcode trap. Keep
            # it as a terminal CFG node; arbitrary NoDecode remains rejected.
            pass
        else:
            raise InventoryError(
                f"{root_name}: unsupported jumpkind {jumpkind!r} at "
                f"{block_address:#x}"
            )

        record = {
            "address": block_address,
            "instructions": instructions,
            "size": block.size,
            "successors": sorted(successors),
        }
        blocks.append(record)
        for successor in sorted(successors):
            if successor not in seen:
                queue.append(successor)

    blocks.sort(key=lambda record: record["address"])
    calls.sort(key=lambda call: call["address"])
    _validate_block_partition(
        root_name=root_name,
        entry=entry,
        extent_end=extent_end,
        blocks=blocks,
    )
    return blocks, calls, walked_indirect_sites


def build_static_cfg(pinned: PinnedBinary) -> dict[str, Any]:
    """Recover and reconcile the rooted CFG using the sole loaded project."""

    roots = pinned.manifest["roots"]
    ordered_roots = sorted(
        roots, key=lambda name: (roots[name]["address"], name)
    )
    root_at_address = {
        root["address"]: name for name, root in roots.items()
    }
    primitive_at_address = {
        address: name
        for name, address in pinned.manifest[
            "primitive_boundaries"
        ].items()
    }

    output_roots: dict[str, Any] = {}
    recovered_call_graph: dict[str, dict[str, int]] = {}
    recovered_indirect: dict[str, list[dict[str, Any]]] = {}

    for root_name in ordered_roots:
        root = roots[root_name]
        entry = root["address"]
        jump_tables = {} if pinned.manifest.get("open_transfers") else _recover_relative_jump_tables(
            pinned, root_name=root_name, root=root)
        blocks, raw_calls, walked_indirect_sites = _walk_function(
            pinned,
            root_name=root_name,
            root=root,
            jump_tables=jump_tables,
        )
        if walked_indirect_sites != set(jump_tables):
            raise InventoryError(
                f"{root_name}: pinned jump table is unreachable: expected="
                f"{sorted(hex(site) for site in jump_tables)}, actual="
                f"{sorted(hex(site) for site in walked_indirect_sites)}"
            )

        calls: list[dict[str, Any]] = []
        call_counts: Counter[str] = Counter()
        for call in raw_calls:
            target = call["target"]
            kind, name = _resolve_call_target(
                target,
                root_at_address=root_at_address,
                primitive_at_address=primitive_at_address,
            )
            if kind == "open" and not pinned.manifest.get("open_transfers"):
                raise InventoryError(f"CFG discovered undeclared call target {target}")
            graph_name = (
                name if kind == "direct-local" else f"{'primitive' if kind == 'modeled-primitive' else 'open'}:{name}"
            )
            call_counts[graph_name] += 1
            calls.append(
                {
                    "address": call["address"],
                    "kind": kind,
                    "name": name,
                    "target": target,
                }
            )

        recovered_call_graph[root_name] = dict(sorted(call_counts.items()))
        expected_calls = pinned.manifest["call_graph"][root_name]
        if not pinned.manifest.get("open_transfers") and recovered_call_graph[root_name] != expected_calls:
            raise InventoryError(
                f"{root_name}: CFG call graph disagrees with the pinned "
                f"inventory: expected={expected_calls!r}, "
                f"actual={recovered_call_graph[root_name]!r}"
            )

        if jump_tables:
            recovered_indirect[root_name] = [
                {
                    "address": address,
                    "targets": jump_tables[address],
                }
                for address in sorted(jump_tables)
            ]

        output_roots[root_name] = {
            "address": entry,
            "blocks": blocks,
            "calls": calls,
            "size": root["size"],
            "symbol": root["symbol"],
            **({key: root[key] for key in ("image_sha256", "object_path") if key in root}),
        }

    return {
        "call_graph": recovered_call_graph,
        "image_sha256": pinned.manifest["image_sha256"],
        "indirect_jumps": recovered_indirect,
        "roots": output_roots,
        "schema": 1,
    }

