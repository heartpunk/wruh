"""Narrowly recognized architectural terminal instructions."""

from __future__ import annotations

from typing import Any


def is_ud2_instruction(instruction: dict[str, Any]) -> bool:
    """Return true only for the exact AMD64 UD2 instruction encoding."""

    return (
        instruction.get("mnemonic", "").lower() == "ud2"
        and instruction.get("bytes", "").lower() == "0f0b"
        and instruction.get("size") == 2
    )


def is_ud2_no_decode_terminal(
    jumpkind: str,
    instructions: list[dict[str, Any]],
    *,
    block_end: int,
    has_zero_length_imark: bool,
) -> bool:
    """Recognize only a fully decoded NoDecode block ending in exact UD2."""

    if jumpkind != "Ijk_NoDecode" or has_zero_length_imark or not instructions:
        return False
    terminal = instructions[-1]
    return (
        is_ud2_instruction(terminal)
        and terminal["address"] + terminal["size"] == block_end
    )
