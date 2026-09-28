"""Temporary runtime-closure tracing for extraction actions."""

from __future__ import annotations

import atexit
from collections import Counter
import cProfile
import importlib.machinery
import json
import os
from pathlib import Path
import pstats
import sys
import time
from typing import Any


_AUDIT_EVENTS = {
    "ctypes.dlopen",
    "os.exec",
    "os.posix_spawn",
    "os.spawn",
    "os.system",
    "subprocess.Popen",
}
_STARTED = False


def _bounded_repr(value: object, limit: int = 4096) -> str:
    try:
        rendered = repr(value)
    except Exception as error:  # pragma: no cover - diagnostic fallback
        rendered = f"<repr failed: {type(error).__name__}: {error}>"
    if len(rendered) > limit:
        return rendered[:limit] + "...<truncated>"
    return rendered


def _mapped_files() -> tuple[list[str], list[str]]:
    maps_path = Path("/proc/self/maps")
    if not maps_path.is_file():
        return [], []
    lines = maps_path.read_text(encoding="utf-8").splitlines()
    files = sorted(
        {
            fields[5]
            for line in lines
            if len(fields := line.split(maxsplit=5)) == 6
            and fields[5].startswith("/")
        }
    )
    return files, lines


def _module_inventory() -> list[dict[str, Any]]:
    result = []
    for name, module in sorted(sys.modules.items()):
        if module is None:
            continue
        spec = getattr(module, "__spec__", None)
        loader = getattr(spec, "loader", None)
        path = getattr(module, "__file__", None)
        result.append(
            {
                "name": name,
                "file": None if path is None else os.fspath(path),
                "loader": None if loader is None else type(loader).__name__,
                "native_extension": isinstance(
                    loader,
                    importlib.machinery.ExtensionFileLoader,
                ),
            }
        )
    return result


def _profile_summary(profile: cProfile.Profile) -> list[dict[str, Any]]:
    stats = pstats.Stats(profile).stats
    rows = []
    for (filename, line, function), values in stats.items():
        primitive_calls, total_calls, total_time, cumulative_time, _callers = values
        if filename != "~":
            continue
        rows.append(
            {
                "function": function,
                "primitive_calls": primitive_calls,
                "total_calls": total_calls,
                "total_time_seconds": total_time,
                "cumulative_time_seconds": cumulative_time,
                "line": line,
            }
        )
    rows.sort(
        key=lambda row: (
            -row["cumulative_time_seconds"],
            -row["total_calls"],
            row["function"],
        )
    )
    return rows[:500]


def start_runtime_trace() -> None:
    """Start process-local tracing when the Bazel action declares an output."""

    global _STARTED
    output = os.environ.get("GHOT_RUNTIME_TRACE_OUTPUT")
    if _STARTED or not output:
        return
    _STARTED = True

    started_wall = time.time()
    started_monotonic = time.monotonic()
    audit_events: list[dict[str, Any]] = []
    audit_counts: Counter[str] = Counter()

    def audit(event: str, arguments: tuple[object, ...]) -> None:
        if event not in _AUDIT_EVENTS:
            return
        audit_counts[event] += 1
        if len(audit_events) < 2000:
            audit_events.append(
                {
                    "event": event,
                    "arguments": _bounded_repr(arguments),
                    "elapsed_seconds": time.monotonic() - started_monotonic,
                }
            )

    sys.addaudithook(audit)
    profile = cProfile.Profile()
    profile.enable()

    def finish() -> None:
        profile.disable()
        mapped_files, maps = _mapped_files()
        document = {
            "schema": "ghot-extraction-runtime-trace-v1",
            "pid": os.getpid(),
            "argv": sys.argv,
            "executable": sys.executable,
            "platform": sys.platform,
            "started_unix_seconds": started_wall,
            "elapsed_seconds": time.monotonic() - started_monotonic,
            "modules": _module_inventory(),
            "mapped_files": mapped_files,
            "proc_self_maps": maps,
            "audit_event_counts": dict(sorted(audit_counts.items())),
            "audit_events": audit_events,
            "native_profile": _profile_summary(profile),
        }
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(document, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )

    atexit.register(finish)
