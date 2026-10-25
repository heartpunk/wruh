#!/usr/bin/env python3
"""Copy sealed Bazel census outputs before the full invocation finishes."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import tempfile
from pathlib import Path


TARGET_PATTERN = re.compile(r"^binary_census_([a-z0-9]+)_remote_test$")


def _has_run_provenance(report: Path, run_identifier: str, revision_identifier: str) -> bool:
    try:
        graph = json.loads(report.read_text(encoding="utf-8")).get("@graph", [])
    except (OSError, ValueError):
        return False
    identifiers: set[str] = set()
    for node in graph:
        value = node.get("bfe:identifier")
        if isinstance(value, str):
            identifiers.add(value)
        elif isinstance(value, list):
            identifiers.update(item for item in value if isinstance(item, str))
    return run_identifier in identifiers and revision_identifier in identifiers


def _has_global_failure_provenance(
    summary: Path,
    *,
    target_id: str,
    run_identifier: str,
    revision_identifier: str,
) -> bool:
    try:
        payload = json.loads(summary.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(payload, dict):
        return False
    provenance = payload.get("provenance", {})
    return (
        payload.get("targetId") == target_id
        and isinstance(payload.get("globalFailure"), dict)
        and isinstance(provenance, dict)
        and provenance.get("run") == run_identifier
        and provenance.get("revision") == revision_identifier
    )


def collect(
    testlogs: Path,
    report_root: Path,
    *,
    run_identifier: str,
    revision_identifier: str,
) -> set[str]:
    collected: set[str] = set()
    extractor_logs = testlogs / "extractor"
    if not extractor_logs.exists():
        return collected

    for test_root in extractor_logs.glob("binary_census_*_remote_test"):
        target_match = TARGET_PATTERN.match(test_root.name)
        if target_match is None:
            continue
        target = target_match.group(1)
        outputs_root = test_root / "test.outputs"
        for summary in outputs_root.rglob("summary.json"):
            if not summary.is_file():
                continue
            report = summary.parent / "census.jsonld"
            has_report_provenance = report.is_file() and _has_run_provenance(
                report, run_identifier, revision_identifier
            )
            has_failure_provenance = _has_global_failure_provenance(
                summary,
                target_id=target,
                run_identifier=run_identifier,
                revision_identifier=revision_identifier,
            )
            if not has_report_provenance and not has_failure_provenance:
                continue

            shard_name = summary.parent.relative_to(outputs_root)
            destination = report_root / target
            if str(shard_name) != ".":
                destination /= shard_name
            marker = destination / ".collected"
            if marker.exists():
                continue

            destination.parent.mkdir(parents=True, exist_ok=True)
            staging = Path(tempfile.mkdtemp(prefix=".census-collect-", dir=destination.parent))
            try:
                shutil.copytree(summary.parent, staging, dirs_exist_ok=True)
                (staging / ".collected").touch()
                if destination.exists():
                    shutil.rmtree(destination)
                os.replace(staging, destination)
            finally:
                if staging.exists():
                    shutil.rmtree(staging)
            collected.add(target)
    return collected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--testlogs", type=Path, required=True)
    parser.add_argument("--report-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    parser.add_argument("--checked-out-sha", required=True)
    args = parser.parse_args()
    for target in sorted(collect(
        args.testlogs,
        args.report_root,
        run_identifier=f"github-actions-run:{args.run_id}/attempt/{args.run_attempt}",
        revision_identifier=f"git-commit:{args.checked_out_sha}",
    )):
        print(f"Collected completed census outputs for {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
