"""Linear instruction occurrence inventory, independent of reachability.

The caller supplies selected byte spans and explicit data intervals. Decoding is
completed before work is partitioned so that a chunk boundary cannot invent an
x86 instruction boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Any, Iterable


@dataclass(frozen=True)
class Span:
    address: int
    data: bytes

    @property
    def end(self) -> int:
        return self.address + len(self.data)


@dataclass(frozen=True)
class Instruction:
    address: int
    data: bytes
    mnemonic: str
    operands: str


@dataclass(frozen=True)
class Interval:
    start: int
    end: int


@dataclass(frozen=True)
class Inventory:
    decoded: tuple[Instruction, ...]
    unresolved: tuple[Interval, ...]
    unexamined: tuple[Interval, ...]


def inventory(spans: Iterable[Span], data_intervals: Iterable[Interval], decoder: Any) -> Inventory:
    """Decode selected spans, recording failures and explicitly excluded data.

    Intervals are half-open. An undecodable byte is examined but unresolved. The remainder of that
    contiguous code span is unexamined because its next instruction boundary
    is unknown. Excluded data is never passed to the decoder, including as
    part of an instruction crossing its boundary.
    """
    spans = tuple(sorted(spans, key=lambda span: span.address))
    exclusions = tuple(sorted(data_intervals, key=lambda item: item.start))
    if any(span.address < 0 or not span.data for span in spans):
        raise ValueError("spans must be nonempty and have nonnegative addresses")
    if any(a.end > b.address for a, b in zip(spans, spans[1:])):
        raise ValueError("selected spans overlap")
    if any(item.start < 0 or item.start >= item.end for item in exclusions):
        raise ValueError("invalid data interval")
    if any(a.end > b.start for a, b in zip(exclusions, exclusions[1:])):
        raise ValueError("data intervals overlap")

    decoded: list[Instruction] = []
    unresolved: list[Interval] = []
    unexamined: list[Interval] = []
    for span in spans:
        cursor = span.address
        for excluded in (*exclusions, Interval(span.end, span.end)):
            if excluded.end <= cursor and excluded.start != span.end:
                continue
            if excluded.start >= span.end:
                boundary = span.end
            else:
                boundary = max(cursor, excluded.start)
            while cursor < boundary:
                offset = cursor - span.address
                code = span.data[offset:min(offset + 15, boundary - span.address)]
                instruction = next(iter(decoder.disasm(code, cursor, count=1)), None)
                if instruction is None:
                    unresolved.append(Interval(cursor, cursor + 1))
                    cursor += 1
                    if cursor < boundary:
                        unexamined.append(Interval(cursor, boundary))
                        cursor = boundary
                    break
                size = instruction.size
                if (instruction.address != cursor or size <= 0 or size > len(code)
                        or bytes(instruction.bytes) != code[:size]):
                    raise ValueError("decoder returned an invalid instruction")
                decoded.append(Instruction(cursor, bytes(instruction.bytes), instruction.mnemonic, instruction.op_str))
                cursor += size
            if excluded.start >= span.end:
                break
            end = min(span.end, excluded.end)
            if cursor < end:
                unexamined.append(Interval(cursor, end))
                cursor = end
    return Inventory(tuple(decoded), tuple(unresolved), tuple(unexamined))


def shuffled_chunks(result: Inventory, chunk_size: int, seed: int) -> tuple[tuple[Instruction, ...], ...]:
    """Partition decoded occurrences, then shuffle chunks without changing them."""
    if chunk_size <= 0:
        raise ValueError("chunk size must be positive")
    chunks = [result.decoded[i:i + chunk_size] for i in range(0, len(result.decoded), chunk_size)]
    random.Random(seed).shuffle(chunks)
    return tuple(chunks)
