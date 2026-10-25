"""Serialize the census coordinator's run manifest as JSON."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence


def build_manifest(
    *,
    wruh_revision: str,
    run_id: str,
    run_attempt: str,
    requested_targets: Sequence[str],
    collected_targets: Sequence[str],
    status: str,
) -> dict[str, object]:
    return {
        "schemaVersion": 1,
        "wruhRevision": wruh_revision,
        "runId": run_id,
        "runAttempt": run_attempt,
        "requestedTargets": list(requested_targets),
        "collectedTargets": list(collected_targets),
        "status": status,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wruh-revision", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    parser.add_argument("--requested-targets", nargs="+", required=True)
    parser.add_argument("--collected-targets", nargs="*", default=[])
    parser.add_argument("--status", choices=("running", "complete", "incomplete"), required=True)
    args = parser.parse_args()
    json.dump(build_manifest(
        wruh_revision=args.wruh_revision,
        run_id=args.run_id,
        run_attempt=args.run_attempt,
        requested_targets=args.requested_targets,
        collected_targets=args.collected_targets,
        status=args.status,
    ), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
