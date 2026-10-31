"""Fresh, per-encoding WRUH hints for generated-instruction selection.

Hints guide generation only: they are neither an admission policy nor a
correctness oracle. A missing or failed extraction is never a passing test.
"""
from __future__ import annotations

from concurrent.futures import Executor, Future
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class HintKey:
    encoding: bytes
    source: int
    extractor_revision: str

    def __post_init__(self) -> None:
        if not self.encoding or len(self.encoding) > 15:
            raise ValueError("expected one x86 instruction encoding")
        if not 0 <= self.source < 1 << 64 or not self.extractor_revision:
            raise ValueError("source address and extractor revision are required")


@dataclass(frozen=True)
class DependencyHint:
    reads: frozenset[str]
    writes: frozenset[str]


def extract_hint(key: HintKey) -> DependencyHint:
    """Extract one exact encoding using WRUH's instruction-step extractor.

    The resulting sets are syntactic hints, not exact semantic footprints.
    Full state includes identity assignments; those must not imply every
    register is read and written by every instruction.
    """
    import angr
    import z3
    from extractor.amd64_state import step_instruction_outcomes

    project = angr.load_shellcode(key.encoding, arch="amd64", load_address=key.source)
    instruction = project.factory.block(key.source, num_inst=1).capstone.insns
    if len(instruction) != 1 or instruction[0].size != len(key.encoding):
        raise ValueError("encoding does not decode to exactly one instruction")
    family = step_instruction_outcomes(project, key.source)
    reads: set[str] = set()
    writes: set[str] = set()
    for outcome in family.outcomes:
        expressions = [family.source_guard, outcome.guard, outcome.target]
        for name, value in outcome.updates.items():
            if z3.is_const(value) and value.decl().kind() == z3.Z3_OP_UNINTERPRETED and str(value) == name:
                continue
            writes.add(name)
            expressions.append(value)
        for expr in expressions:
            for variable in z3.z3util.get_vars(expr):
                reads.add(str(variable))
    return DependencyHint(frozenset(reads), frozenset(writes))


class HintCache:
    """Submit extraction once for each exact instruction and provenance key."""

    def __init__(self, executor: Executor, extractor: Callable[[HintKey], DependencyHint] = extract_hint):
        self.executor = executor
        self.extractor = extractor
        self._pending: dict[HintKey, Future[DependencyHint]] = {}

    def enqueue(self, key: HintKey) -> Future[DependencyHint]:
        if key not in self._pending:
            self._pending[key] = self.executor.submit(self.extractor, key)
        return self._pending[key]
