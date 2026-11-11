"""Fixed, bounded PR census target selector over archived JSON-LD records.

The caller owns the regression sample seed. Hypothesis files contain only
typed Wruh failure-kind IRIs; arbitrary query text is never evaluated.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

POLICY_VERSION = "wruh-pr-selector-v1"
HYPOTHESIS_IRIS = re.compile(r"wruh:(?:mechanism|failureKind)\s+wruh:(failure[A-Za-z0-9]+)")
KNOWN_FAILURE_KINDS = {
    "failureInventoryOverlap", "failureMetadata", "failureNoDecode",
    "failureUnexpectedTrap", "failureUnrecognizedTerminal",
    "failureCallFallthrough", "failureMissingEdge", "failureWrongTarget",
    "failureUnsupportedOperation", "failureSemanticMismatch", "failureRunner",
    "failureCancellation", "failureTimeout", "failureOOM", "failureIncompleteExecution",
}


def read_hypothesis(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    kinds = set(HYPOTHESIS_IRIS.findall(text)) & KNOWN_FAILURE_KINDS
    if not kinds:
        raise ValueError("hypothesis must name at least one typed wruh:FailureKind")
    return {"https://github.com/heartpunk/wruh/blob/main/docs/ontology/wruh.ttl#" + kind for kind in kinds}


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def canonical_inventory(*, target_id: str, binary_sha256: str, architecture: str, policy_version: str,
                        candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Normalize the pinned current inventory before selection or partitioning."""
    normalized = []
    for candidate in candidates:
        candidate_id = candidate["candidateId"]
        address_space = candidate["addressSpace"]
        address = candidate["address"]
        extent = candidate["extent"]
        if not isinstance(candidate_id, str) or not isinstance(address_space, str):
            raise ValueError("candidate identity needs candidateId and addressSpace")
        normalized.append({"candidateId": candidate_id, "addressSpace": address_space,
                           "address": address, "extent": extent})
    ids = [candidate["candidateId"] for candidate in normalized]
    if len(ids) != len(set(ids)):
        raise ValueError("current inventory candidate IDs must be unique")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", binary_sha256):
        raise ValueError("binarySha256 must be a 64-digit SHA-256 digest")
    return {"schemaVersion": 1, "targetId": target_id, "binarySha256": binary_sha256.lower(),
            "architecture": architecture,
            "inventoryPolicyVersion": policy_version,
            "candidates": sorted(normalized, key=lambda candidate: candidate["candidateId"])}


def build_selection_manifest(inventory: dict[str, Any], hypothesis_kinds: set[str],
                             history: list[dict[str, Any]], *, history_coverage_complete: bool,
                             seed: int, sample_size: int,
                             evidence_gaps: list[str] | None = None) -> dict[str, Any]:
    """Match typed historical diagnoses only by exact binary and candidate ID.

    The history producer must establish complete evidence coverage. Legacy
    BFE archives do not contain typed diagnoses/coverage, so callers must pass
    false and receive a pinned mode=all manifest.
    """
    inventory_digest = "sha256:" + hashlib.sha256(canonical_bytes(inventory)).hexdigest()
    candidate_ids = {candidate["candidateId"] for candidate in inventory["candidates"]}
    gaps = list(evidence_gaps or [])
    matched: set[str] = set()
    covered: set[str] = set()
    proven = history_coverage_complete and not gaps
    for record in history:
        if (record.get("binarySha256", "").lower() != inventory["binarySha256"]
                or record.get("evidenceState") != "known"
                or record.get("evidenceReference") is None):
            proven = False
            gaps.append("historical-evidence-unmapped-or-unknown")
            continue
        candidate_id = record.get("candidateId")
        if candidate_id not in candidate_ids:
            proven = False
            gaps.append("historical-candidate-not-in-current-inventory")
            continue
        covered.add(candidate_id)
        if record.get("failureKind") in hypothesis_kinds:
            matched.add(candidate_id)

    if not candidate_ids.issubset(covered):
        proven = False
        gaps.append("historical-evidence-does-not-cover-current-inventory")

    if not proven:
        manifest = {"schemaVersion": 1, "selectionPolicyVersion": POLICY_VERSION,
                    "inventoryDigest": inventory_digest, "mode": "all", "candidateIds": [],
                    "selectionReasons": [{"reason": "unknown-or-unmappable-historical-evidence"}],
                    "evidenceGaps": sorted(set(gaps or ["historical-evidence-coverage-unknown"])),
                    "evidenceReferences": sorted({str(r.get("evidenceReference")) for r in history if r.get("evidenceReference")})}
    else:
        complement = sorted(candidate_ids - matched)
        sampled = sorted(complement, key=lambda candidate_id: (
            hashlib.sha256(b"wruh-pr-regression-sample-v1\0" + str(seed).encode() + b"\0" + candidate_id.encode()).digest(),
            candidate_id,
        ))[:min(max(0, sample_size), len(complement))]
        selected = sorted(matched | set(sampled))
        manifest = {"schemaVersion": 1, "selectionPolicyVersion": POLICY_VERSION,
                    "inventoryDigest": inventory_digest, "mode": "explicit", "candidateIds": selected,
                    "seed": seed, "sampleStrata": ["unmatched-current-inventory-candidates"],
                    "sampleSize": len(sampled),
                    "selectionReasons": ([{"candidateId": item, "reason": "typed-historical-failure-match"} for item in sorted(matched)]
                                         + [{"candidateId": item, "reason": "seeded-complement-sample"} for item in sampled]),
                    "evidenceGaps": [],
                    "evidenceReferences": sorted({str(r["evidenceReference"]) for r in history if r.get("evidenceReference")})}
    manifest_digest = "sha256:" + hashlib.sha256(canonical_bytes(manifest)).hexdigest()
    return {"manifest": manifest, "manifestDigest": manifest_digest}


def load_selection_history(paths: list[Path], *, binary_sha256: str) -> tuple[list[dict[str, Any]], bool, list[str]]:
    """Read only normalized, provenance-bearing records from the archive adapter.

    Legacy census JSON-LD is intentionally not reinterpreted as typed diagnoses.
    """
    records: list[dict[str, Any]] = []
    gaps: list[str] = []
    complete = bool(paths)
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            complete = False
            gaps.append(f"{path.name}:unknown")
            continue
        if (not isinstance(payload, dict) or payload.get("selectionHistoryVersion") != 1
                or payload.get("evidenceCoverage") != "complete"
                or str(payload.get("binarySha256", "")).lower() != binary_sha256.lower()
                or not isinstance(payload.get("records"), list)):
            complete = False
            gaps.append(f"{path.name}:legacy-or-unverified-history-format")
            continue
        records.extend(item for item in payload["records"] if isinstance(item, dict))
    return records, complete, gaps


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--hypothesis", type=Path, required=True)
    parser.add_argument("--records", type=Path, nargs="*", default=[])
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--sample-size", type=int, default=2)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--binary-sha256", required=True)
    parser.add_argument("--architecture", required=True)
    parser.add_argument("--inventory-policy-version", required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records, coverage_complete, gaps = load_selection_history(args.records, binary_sha256=args.binary_sha256)
    inventory_payload = json.loads(args.inventory.read_text(encoding="utf-8"))
    inventory = canonical_inventory(target_id=args.target_id, binary_sha256=args.binary_sha256,
                                    architecture=args.architecture,
                                    policy_version=args.inventory_policy_version,
                                    candidates=inventory_payload["candidates"])
    result = build_selection_manifest(inventory, read_hypothesis(args.hypothesis), records,
                                      history_coverage_complete=coverage_complete, seed=args.seed,
                                      sample_size=args.sample_size,
                                      evidence_gaps=gaps)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
