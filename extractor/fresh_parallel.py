"""Fork-parallel fresh extraction over the fixed TinyMemory root family."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import os
from typing import Any

from extractor.binary_inventory import PinnedBinary
from extractor.fresh import FreshExtractionError, FreshFunction, extract_fresh_function


_FORK_PINNED: PinnedBinary | None = None
_FORK_CFG: dict[str, Any] | None = None


def _fork_worker(function_id: str) -> FreshFunction:
    if _FORK_PINNED is None or _FORK_CFG is None:
        raise FreshExtractionError("fresh worker started without inherited context")
    return extract_fresh_function(_FORK_PINNED, _FORK_CFG, function_id)


def extract_fresh_functions(
    pinned: PinnedBinary,
    cfg: dict[str, Any],
    function_ids: tuple[str, ...] | None = None,
    *,
    max_workers: int | None = None,
) -> tuple[FreshFunction, ...]:
    """Extract one function per fork-worker and merge by canonical root order."""

    roots = cfg.get("roots")
    if not isinstance(roots, dict) or not roots:
        raise FreshExtractionError("CFG has no rooted functions")
    canonical = tuple(
        sorted(roots, key=lambda name: (roots[name]["address"], name))
    )
    selected = canonical if function_ids is None else function_ids
    if len(set(selected)) != len(selected) or set(selected) - set(canonical):
        raise FreshExtractionError("parallel function selection is invalid")
    selected = tuple(name for name in canonical if name in set(selected))
    if not selected:
        raise FreshExtractionError("parallel function selection is empty")

    workers = max_workers or min(len(selected), os.cpu_count() or 1)
    if type(workers) is not int or not 1 <= workers <= len(selected):
        raise FreshExtractionError("parallel worker count is invalid")
    if workers == 1:
        return tuple(
            extract_fresh_function(pinned, cfg, function_id)
            for function_id in selected
        )

    global _FORK_PINNED, _FORK_CFG
    _FORK_PINNED = pinned
    _FORK_CFG = cfg
    try:
        context = multiprocessing.get_context("fork")
        with ProcessPoolExecutor(
            max_workers=workers,
            mp_context=context,
        ) as executor:
            results = tuple(executor.map(_fork_worker, selected))
    finally:
        _FORK_PINNED = None
        _FORK_CFG = None
    if tuple(result.function_id for result in results) != selected:
        raise FreshExtractionError("parallel result order is not deterministic")
    return results
