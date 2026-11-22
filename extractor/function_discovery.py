"""Heuristic CFGFast entry discovery with explicit, scoped block evidence.

A recovered block envelope is an extraction scope, never an ELF symbol size or
evidence that the whole source-level function has been recovered.
"""

from __future__ import annotations

import math
import signal
import threading
import time
from collections import Counter
from contextlib import contextmanager
from typing import Any


class FunctionDiscoveryError(ValueError):
    """The image cannot supply a bounded main-object discovery scope."""


class _DiscoveryTimeout(BaseException):
    pass


def _union_bytes(ranges: list[tuple[int, int]]) -> int:
    total = 0
    previous_end = -1
    for start, end in sorted(ranges):
        total += max(0, end - max(start, previous_end))
        previous_end = max(previous_end, end)
    return total


def _executable_ranges(image: Any) -> list[tuple[int, int]]:
    """Prefer section file ranges; fall back to file-backed load segments."""
    sections = list(getattr(image, "sections", ()))
    sections = [section for section in sections if getattr(section, "is_executable", False)]
    regions = sections or [segment for segment in getattr(image, "segments", ())
                           if getattr(segment, "is_executable", False)]
    ranges = []
    for region in regions:
        if str(getattr(region, "name", "")).startswith((".plt", ".iplt")):
            continue
        start = int(region.vaddr)
        memory_size = int(getattr(region, "memsize", 0))
        size = min(memory_size, int(getattr(region, "filesize", memory_size)))
        if start >= 0 and size > 0:
            ranges.append((start, start + size))
    if not ranges:
        raise FunctionDiscoveryError("main object has no file-backed executable discovery ranges")
    return sorted(set(ranges))


def _within(start: int, end: int, ranges: list[tuple[int, int]]) -> bool:
    return start < end and any(lo <= start and end <= hi for lo, hi in ranges)


@contextmanager
def _wall_clock_guard(seconds: float):
    """Require a hard guard without replacing another caller's active timer."""
    usable = (threading.current_thread() is threading.main_thread()
              and hasattr(signal, "setitimer") and hasattr(signal, "ITIMER_REAL"))
    if not usable:
        raise FunctionDiscoveryError("bounded CFGFast discovery requires the main thread and POSIX ITIMER_REAL")
    if signal.getitimer(signal.ITIMER_REAL) != (0.0, 0.0):
        raise FunctionDiscoveryError("bounded CFGFast discovery cannot replace an active caller SIGALRM timer")
    previous_handler = signal.getsignal(signal.SIGALRM)

    def expired(_signum, _frame):
        raise _DiscoveryTimeout()

    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield True
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


def discover_function_candidates(
    project: Any,
    symbols: list[dict[str, Any]],
    *,
    timeout_seconds: float = 300.0,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Union retained symbol entries with eligible CFGFast entry candidates.

    ``block_ranges`` contains [object-relative address, byte size] pairs.
    A complete status means the configured heuristic analysis returned without
    interruption; it never means all binary functions have been discovered.
    A hard interruption discards the unfinalized CFG's candidates. A graceful
    CFGFast abort may retain finalized partial evidence, marked incomplete.
    """
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError("discovery timeout must be finite and positive")
    image = project.loader.main_object
    executable = _executable_ranges(image)
    started = time.monotonic()
    deadline = started + timeout_seconds
    timed_out = False

    def progress(_percentage, **kwargs):
        nonlocal timed_out
        if time.monotonic() >= deadline:
            timed_out = True
            cfg = kwargs.get("cfg")
            if cfg is not None:
                cfg.abort()

    parameters = {
        "regions": [list(item) for item in executable],
        "symbols": True,
        "function_prologues": False,
        "normalize": False,
        "force_complete_scan": False,
        "force_smart_scan": False,
        "resolve_indirect_jumps": False,
        "data_references": False,
        "cross_references": False,
        "start_at_entry": True,
        "eh_frame": True,
        "detect_tail_calls": False,
    }
    metadata: dict[str, Any] = {
        "schema": "wruh-cfgfast-function-discovery-v1",
        "method": "angr-CFGFast",
        "status": "complete",
        "timed_out": False,
        "timeout_seconds": timeout_seconds,
        "timeout_enforcement": "unavailable",
        "parameters": parameters,
        "main_object_only": True,
        "executable_bytes": _union_bytes(executable),
        "retained_symbol_candidate_count": len(symbols),
        "scope_note": (
            "Heuristic entry and recovered-block evidence; envelopes are extraction scopes, "
            "not declared symbol extents or claims of complete function recovery."
        ),
    }
    result = None
    try:
        with _wall_clock_guard(timeout_seconds) as guarded:
            if guarded:
                metadata["timeout_enforcement"] = "SIGALRM-and-cooperative-progress"
            cfg = project.analyses.CFGFast(
                objects=[image],
                show_progressbar=False,
                progress_callback=progress,
                **parameters,
            )
            if getattr(cfg, "should_abort", False):
                metadata["status"] = "incomplete"
                metadata["reason"] = "timeout" if timed_out else "analysis-aborted"
            result = _collect_candidates(project, symbols, cfg, metadata)
    except _DiscoveryTimeout:
        result = None
        timed_out = True
        metadata.update(status="incomplete", reason="timeout-unfinalized-model-discarded")
    except FunctionDiscoveryError as error:
        result = None
        metadata.update(status="incomplete", reason="timeout-guard-unavailable", diagnostic=str(error))
    except Exception as error:  # noqa: BLE001 -- retain the symbol inventory after provider failures.
        result = None
        metadata.update(status="incomplete", reason="analysis-error",
                        diagnostic=f"{type(error).__name__}: {error}")

    if result is None:
        result = _collect_candidates(project, symbols, None, metadata)
    metadata["timed_out"] = timed_out
    metadata["elapsed_seconds"] = round(time.monotonic() - started, 6)
    if timed_out:
        metadata["status"] = "incomplete"
        metadata.setdefault("reason", "timeout")
    return result


def _collect_candidates(
    project: Any,
    symbols: list[dict[str, Any]],
    cfg: Any,
    metadata: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    image = project.loader.main_object
    mapped_base = int(image.mapped_base)
    linked_base = int(getattr(image, "linked_base", 0))
    executable = [tuple(item) for item in metadata["parameters"]["regions"]]
    retained = {int(candidate["address"]): dict(candidate) for candidate in symbols}
    accepted = []
    rejected: Counter[str] = Counter()
    all_blocks: list[tuple[int, int]] = []
    new_blocks: list[tuple[int, int]] = []
    functions = list(cfg.kb.functions.values()) if cfg is not None else []
    for function in sorted(functions, key=lambda item: int(item.addr)):
        address = int(function.addr)
        if any(getattr(function, flag, False)
               for flag in ("is_plt", "is_simprocedure", "is_syscall", "is_alignment")):
            rejected["plt-simprocedure-syscall-or-alignment"] += 1
            continue
        if not _within(address, address + 1, executable):
            rejected["entry-outside-main-executable-ranges"] += 1
            continue
        if project.is_hooked(address):
            rejected["hooked-entry"] += 1
            continue
        try:
            blocks = sorted({(int(block.addr), int(block.addr) + int(block.size))
                             for block in function.blocks})
        except Exception as error:  # noqa: BLE001 -- retain per-function discovery diagnostics.
            rejected[f"block-evidence-error:{type(error).__name__}"] += 1
            continue
        if not blocks or any(end <= start for start, end in blocks):
            rejected["empty-or-nonpositive-block-evidence"] += 1
            continue
        if any(not _within(start, end, executable) for start, end in blocks):
            rejected["block-outside-main-executable-ranges"] += 1
            continue
        owner = getattr(project.loader, "find_object_containing", None)
        if owner is not None and any(owner(start) is not image or owner(end - 1) is not image
                                     for start, end in blocks):
            rejected["block-owned-by-another-object"] += 1
            continue
        envelope_start = blocks[0][0]
        envelope_end = max(end for _, end in blocks)
        if envelope_start != address:
            rejected["block-envelope-does-not-start-at-entry"] += 1
            continue
        if not _within(envelope_start, envelope_end, executable):
            rejected["envelope-crosses-executable-range-boundary"] += 1
            continue
        relative = address - mapped_base
        if relative < 0:
            rejected["negative-object-relative-entry"] += 1
            continue
        identifier = f"fn_{relative:016x}"
        size = envelope_end - address
        block_bytes = _union_bytes(blocks)
        candidate = {
            "id": identifier,
            "address": address,
            "relative_address": relative,
            "object_virtual_address": linked_base + relative,
            "size": size,
            "symbol": identifier,
            "aliases": [],
            "identity_basis": "cfgfast",
            "recovered_extent_bytes": size,
            "block_ranges": [[start - mapped_base, end - start] for start, end in blocks],
            "recovered_block_bytes": block_bytes,
            "envelope_has_gaps": block_bytes != size,
        }
        accepted.append(candidate)
        all_blocks.extend(blocks)
        if address not in retained:
            retained[address] = candidate
            new_blocks.extend(blocks)

    metadata.update(
        cfgfast_function_count=len(functions),
        accepted_cfgfast_candidate_count=len(accepted),
        new_candidate_count=len(retained) - len(symbols),
        merged_candidate_count=len(retained),
        recovered_block_union_bytes=_union_bytes(all_blocks),
        new_candidate_block_union_bytes=_union_bytes(new_blocks),
        rejected=dict(sorted(rejected.items())),
        recovered_candidates=accepted,
    )
    return [retained[address] for address in sorted(retained)], metadata
