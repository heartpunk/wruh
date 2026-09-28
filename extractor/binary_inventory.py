"""Fail-closed inventory of the exact TinyMemory extractor artifact."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable

import capstone

from extractor.runtime import _runfiles_root
import angr

_BINARY_RLOCATION_ENV = "GHOT_TINYMEMORY_BINARY_RLOCATION"
_MANIFEST_RLOCATION_ENV = "GHOT_TINYMEMORY_MANIFEST_RLOCATION"
_ROOT_NAMES = (
    "step",
    "dispatch",
    "addi_handler",
    "add_handler",
    "lb_handler",
    "sb_handler",
    "beq_handler",
    "goto_handler",
    "slli_handler",
    "srli_handler",
    "srai_handler",
    "mul_handler",
)
_DECLARED_PRIMITIVES = frozenset({"memcpy"})


class InventoryError(RuntimeError):
    """The linked artifact does not satisfy the pinned rooted inventory."""


class CallKind(Enum):
    DIRECT_LOCAL = "direct-local"
    MODELED_PRIMITIVE = "modeled-primitive"


@dataclass(frozen=True)
class CallResolution:
    """Names attached to one encoded direct target."""

    local_names: tuple[str, ...] = ()
    plt_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class PinnedBinary:
    """The exact artifact, manifest, and sole Angr project for one run."""

    artifact: Path
    manifest: dict[str, Any]
    project: angr.Project


@dataclass(frozen=True)
class InventoryPolicy:
    """Target-specific choices used by the generic inventory walk."""

    root_names: tuple[str, ...]
    declared_primitives: frozenset[str]
    resolve_root_symbol: Callable[[str, list[str]], str]
    require_pic: bool = False


def classify_call(
    *,
    encoded_target: int | None,
    resolution: CallResolution,
    selected_symbols: frozenset[str],
    declared_primitives: frozenset[str] = _DECLARED_PRIMITIVES,
) -> tuple[CallKind, str]:
    """Classify one encoded call without retargeting past its successor."""

    if encoded_target is None:
        raise InventoryError("indirect call is forbidden")

    names = resolution.local_names + resolution.plt_names
    if not names:
        raise InventoryError(f"unresolved direct call target {encoded_target:#x}")
    if len(names) != 1:
        raise InventoryError(
            f"ambiguous direct call target {encoded_target:#x}: {names!r}"
        )

    name = names[0]
    if resolution.local_names:
        return (CallKind.DIRECT_LOCAL, name)
    if name in selected_symbols:
        raise InventoryError(
            f"rooted self-PLT call is forbidden: {name} at {encoded_target:#x}"
        )
    if name not in declared_primitives:
        raise InventoryError(
            f"undeclared external call is forbidden: {name} at "
            f"{encoded_target:#x}"
        )
    return (CallKind.MODELED_PRIMITIVE, name)


def _declared_runfile(environment_name: str) -> Path:
    raw_rlocation = os.environ.get(environment_name)
    if not raw_rlocation:
        raise InventoryError(f"{environment_name} is required")
    runfiles_root = _runfiles_root()
    runfile = (runfiles_root / raw_rlocation).absolute()
    if not runfile.is_relative_to(runfiles_root) or not runfile.is_file():
        raise InventoryError(f"declared runfile is missing: {runfile}")
    return runfile


def _root_symbol_name(root: str, symbol_names: list[str]) -> str:
    legacy_prefix = f"_ZN10tinymemory{len(root)}{root}17h"
    v0_suffix = f"_10tinymemory{len(root)}{root}"
    matches = [
        name
        for name in symbol_names
        if name.startswith(legacy_prefix)
        or (name.startswith("_RNvC") and name.endswith(v0_suffix))
    ]
    if len(matches) != 1:
        raise InventoryError(
            f"expected one pinned Rust symbol for {root}, found {matches!r}"
        )
    return matches[0]


TINYMEMORY_INVENTORY_POLICY = InventoryPolicy(
    root_names=_ROOT_NAMES,
    declared_primitives=_DECLARED_PRIMITIVES,
    resolve_root_symbol=_root_symbol_name,
    require_pic=True,
)


def exact_symbol_inventory_policy(
    root_symbols: tuple[str, ...],
    *,
    declared_primitives: frozenset[str] = frozenset(),
    require_pic: bool = False,
) -> InventoryPolicy:
    """Select arbitrary roots whose inventory IDs are exact ELF symbols."""

    if not root_symbols or len(set(root_symbols)) != len(root_symbols):
        raise InventoryError("exact root symbols must be nonempty and unique")

    def resolve(root: str, symbol_names: list[str]) -> str:
        if symbol_names.count(root) != 1:
            raise InventoryError(
                f"expected one exact symbol for {root}, found "
                f"{symbol_names.count(root)}"
            )
        return root

    return InventoryPolicy(
        root_names=root_symbols,
        declared_primitives=declared_primitives,
        resolve_root_symbol=resolve,
        require_pic=require_pic,
    )


def _function_symbol_at(project: angr.Project, address: int) -> Any | None:
    """Choose one exact, sized in-object function symbol at an address."""

    image = project.loader.main_object
    candidates = [
        symbol
        for symbol in image.symbols
        if symbol.name
        and symbol.size > 0
        and symbol.rebased_addr == address
        and getattr(getattr(symbol, "type", None), "name", "")
        == "TYPE_FUNCTION"
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda symbol: (symbol.size, symbol.name), reverse=True)
    best = candidates[0]
    if any(
        symbol.size == best.size and symbol.name != best.name
        for symbol in candidates[1:]
    ):
        raise InventoryError(
            f"ambiguous in-object function symbols at {address:#x}: "
            f"{sorted(symbol.name for symbol in candidates)!r}"
        )
    return best


def _function_symbol_named(project: angr.Project, name: str) -> Any | None:
    """Resolve one sized function definition owned by the main image."""

    candidates = [
        symbol
        for symbol in project.loader.main_object.symbols
        if symbol.name == name
        and symbol.size > 0
        and getattr(getattr(symbol, "type", None), "name", "")
        == "TYPE_FUNCTION"
    ]
    if len(candidates) > 1:
        raise InventoryError(
            f"ambiguous in-object function definition for {name!r}"
        )
    return candidates[0] if candidates else None


def inventory_project(
    project: angr.Project,
    artifact: Path,
    policy: InventoryPolicy = TINYMEMORY_INVENTORY_POLICY,
) -> dict[str, Any]:
    """Build the stable rooted inventory from an already-loaded image."""

    image = project.loader.main_object
    if project.arch.name != "AMD64" or project.arch.bits != 64:
        raise InventoryError(
            f"unexpected architecture: {project.arch.name}/{project.arch.bits}"
        )
    if policy.require_pic and not image.pic:
        raise InventoryError("extractor artifact must be a PIE")

    symbols = {
        symbol.name: symbol
        for symbol in image.symbols
        if symbol.name and symbol.size > 0
    }

    roots: dict[str, Any] = {}
    root_at_address: dict[int, tuple[str, str]] = {}
    pending: list[str] = []
    for root in policy.root_names:
        symbol_name = policy.resolve_root_symbol(root, sorted(symbols))
        symbol = symbols[symbol_name]
        if symbol.rebased_addr in root_at_address:
            raise InventoryError(
                f"selected roots alias address {symbol.rebased_addr:#x}"
            )
        root_at_address[symbol.rebased_addr] = (root, symbol_name)
        roots[root] = {
            "address": symbol.rebased_addr,
            "size": symbol.size,
            "symbol": symbol_name,
        }
        pending.append(root)

    plt_at_address: dict[int, tuple[str, ...]] = {}
    for name, address in image.plt.items():
        plt_at_address.setdefault(address, ())
        plt_at_address[address] = tuple(
            sorted((*plt_at_address[address], name))
        )

    primitive_boundaries: dict[str, int] = {}
    for primitive in sorted(policy.declared_primitives):
        addresses = [
            address
            for address, names in plt_at_address.items()
            if primitive in names
        ]
        if len(addresses) != 1:
            raise InventoryError(
                f"expected one {primitive} PLT boundary, found {addresses!r}"
            )
        primitive_boundaries[primitive] = addresses[0]

    call_graph: dict[str, Counter[str]] = {}
    indirect_jumps: dict[str, list[dict[str, Any]]] = {}
    visited: set[str] = set()

    while pending:
        root = pending.pop(0)
        if root in visited:
            continue
        visited.add(root)
        call_graph[root] = Counter()
        indirect_jumps[root] = []
        symbol_name = roots[root]["symbol"]
        symbol = symbols[symbol_name]
        code = project.loader.memory.load(symbol.rebased_addr, symbol.size)
        instructions = list(
            project.arch.capstone.disasm(code, symbol.rebased_addr)
        )
        if (
            not instructions
            or instructions[0].address != symbol.rebased_addr
            or instructions[-1].address + instructions[-1].size
            != symbol.rebased_addr + symbol.size
        ):
            raise InventoryError(f"incomplete decode for selected root {root}")

        for instruction in instructions:
            if instruction.mnemonic.startswith("call"):
                if len(instruction.operands) != 1:
                    raise InventoryError(
                        f"ambiguous call operands at {instruction.address:#x}"
                    )
                operand = instruction.operands[0]
                encoded_target = (
                    operand.imm
                    if operand.type == capstone.x86.X86_OP_IMM
                    else None
                )
                local = root_at_address.get(encoded_target)
                if local is None and encoded_target is not None:
                    local_symbol = _function_symbol_at(project, encoded_target)
                    if local_symbol is not None:
                        local_id = local_symbol.name
                        existing = roots.get(local_id)
                        if existing is not None and (
                            existing["address"] != local_symbol.rebased_addr
                            or existing["symbol"] != local_symbol.name
                        ):
                            raise InventoryError(
                                f"discovered function identity collision: {local_id}"
                            )
                        roots.setdefault(
                            local_id,
                            {
                                "address": local_symbol.rebased_addr,
                                "size": local_symbol.size,
                                "symbol": local_symbol.name,
                            },
                        )
                        root_at_address[local_symbol.rebased_addr] = (
                            local_id,
                            local_symbol.name,
                        )
                        pending.append(local_id)
                        local = (local_id, local_symbol.name)
                plt_names = plt_at_address.get(encoded_target, ())
                if local is None and len(plt_names) == 1:
                    self_plt_symbol = _function_symbol_named(project, plt_names[0])
                    if self_plt_symbol is not None:
                        local_id = self_plt_symbol.name
                        roots.setdefault(
                            local_id,
                            {
                                "address": self_plt_symbol.rebased_addr,
                                "size": self_plt_symbol.size,
                                "symbol": self_plt_symbol.name,
                            },
                        )
                        root_at_address[self_plt_symbol.rebased_addr] = (
                            local_id,
                            self_plt_symbol.name,
                        )
                        pending.append(local_id)
                        local = (local_id, self_plt_symbol.name)
                resolution = CallResolution(
                    local_names=(() if local is None else (local[1],)),
                    plt_names=(() if local is not None else plt_names),
                )
                kind, target_name = classify_call(
                    encoded_target=encoded_target,
                    resolution=resolution,
                    selected_symbols=frozenset(
                        selected["symbol"] for selected in roots.values()
                    ),
                    declared_primitives=policy.declared_primitives,
                )
                if kind is CallKind.DIRECT_LOCAL:
                    if local is None:
                        raise InventoryError(
                            f"unmanifested local call target {encoded_target:#x}"
                        )
                    call_graph[root][local[0]] += 1
                else:
                    call_graph[root][f"primitive:{target_name}"] += 1
                continue

            if not instruction.mnemonic.startswith("jmp"):
                continue
            if len(instruction.operands) != 1:
                raise InventoryError(
                    f"ambiguous jump operands at {instruction.address:#x}"
                )
            operand = instruction.operands[0]
            if operand.type == capstone.x86.X86_OP_IMM:
                if not (
                    symbol.rebased_addr
                    <= operand.imm
                    < symbol.rebased_addr + symbol.size
                ):
                    raise InventoryError(
                        f"tail-call jump from {root} at "
                        f"{instruction.address:#x} to {operand.imm:#x}"
                    )
                continue
            indirect_jumps[root].append(
                {
                    "address": instruction.address,
                    "bytes": instruction.bytes.hex(),
                    "operand": instruction.op_str,
                }
            )

    return {
        "arch": project.arch.name,
        "bits": project.arch.bits,
        "call_graph": {
            root: dict(sorted(call_graph[root].items()))
            for root in roots
        },
        "image_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "indirect_jumps": {
            root: indirect_jumps[root]
            for root in roots
            if indirect_jumps[root]
        },
        "pic": bool(image.pic),
        "primitive_boundaries": primitive_boundaries,
        "roots": roots,
        "schema": 1,
    }


def inventory(artifact: Path) -> dict[str, Any]:
    """Load one image and build its stable rooted inventory."""

    project = angr.Project(str(artifact), auto_load_libs=False)
    return inventory_project(project, artifact)


def load_pinned_binary() -> PinnedBinary:
    """Load and validate the exact artifact without creating a second project."""

    artifact = _declared_runfile(_BINARY_RLOCATION_ENV)
    manifest_path = _declared_runfile(_MANIFEST_RLOCATION_ENV)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    project = angr.Project(str(artifact), auto_load_libs=False)
    actual = inventory_project(project, artifact)
    if actual != manifest:
        raise InventoryError(
            "extractor artifact inventory differs from the pinned manifest:\n"
            f"expected={json.dumps(manifest, sort_keys=True)}\n"
            f"actual={json.dumps(actual, sort_keys=True)}"
        )
    return PinnedBinary(
        artifact=artifact,
        manifest=manifest,
        project=project,
    )


def validate_pinned_artifact() -> dict[str, Any]:
    return load_pinned_binary().manifest


def main() -> None:
    print(json.dumps(validate_pinned_artifact(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
