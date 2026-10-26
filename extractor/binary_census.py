"""Run a per-function census over a pinned binary and emit PROV-O JSON-LD."""

from __future__ import annotations

import argparse
import gc
import gzip
import hashlib
import importlib.metadata
import io
import json
import logging
import os
import platform
import tarfile
import time
import uuid
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path
from typing import Any

BFE = "https://github.com/heartpunk/wruh/blob/main/docs/proposal/ontology/binary-function-extraction.ttl#"
PROV = "http://www.w3.org/ns/prov#"
XSD = "http://www.w3.org/2001/XMLSchema#"

JSONLD_CONTEXT: dict[str, Any] = {
    "bfe": BFE,
    "prov": PROV,
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": XSD,
    "prov:used": {"@id": "prov:used", "@type": "@id"},
    "prov:wasGeneratedBy": {"@id": "prov:wasGeneratedBy", "@type": "@id"},
    "prov:wasInformedBy": {"@id": "prov:wasInformedBy", "@type": "@id"},
    "prov:wasAssociatedWith": {"@id": "prov:wasAssociatedWith", "@type": "@id"},
    "prov:wasDerivedFrom": {"@id": "prov:wasDerivedFrom", "@type": "@id"},
    "prov:hadMember": {"@id": "prov:hadMember", "@type": "@id"},
    "prov:startedAtTime": {"@id": "prov:startedAtTime", "@type": "xsd:dateTime"},
    "prov:endedAtTime": {"@id": "prov:endedAtTime", "@type": "xsd:dateTime"},
    "bfe:hasBinaryObject": {"@id": "bfe:hasBinaryObject", "@type": "@id"},
    "bfe:inventoryGenerationUsesImage": {"@id": "bfe:inventoryGenerationUsesImage", "@type": "@id"},
    "bfe:inventoryGenerationUsesPolicy": {"@id": "bfe:inventoryGenerationUsesPolicy", "@type": "@id"},
    "bfe:generatesInventory": {"@id": "bfe:generatesInventory", "@type": "@id"},
    "bfe:hasCandidate": {"@id": "bfe:hasCandidate", "@type": "@id"},
    "bfe:censusUsesImage": {"@id": "bfe:censusUsesImage", "@type": "@id"},
    "bfe:censusUsesInventory": {"@id": "bfe:censusUsesInventory", "@type": "@id"},
    "bfe:censusGeneratesEntry": {"@id": "bfe:censusGeneratesEntry", "@type": "@id"},
    "bfe:activityUsesToolRelease": {"@id": "bfe:activityUsesToolRelease", "@type": "@id"},
    "bfe:inventoryGenerationUsesToolRelease": {"@id": "bfe:inventoryGenerationUsesToolRelease", "@type": "@id"},
    "bfe:attemptsCandidate": {"@id": "bfe:attemptsCandidate", "@type": "@id"},
    "bfe:entryRecordsCandidate": {"@id": "bfe:entryRecordsCandidate", "@type": "@id"},
    "bfe:entryHasAttempt": {"@id": "bfe:entryHasAttempt", "@type": "@id"},
    "bfe:entryDisposition": {"@id": "bfe:entryDisposition", "@type": "@id"},
    "bfe:generatesArtifact": {"@id": "bfe:generatesArtifact", "@type": "@id"},
    "bfe:observesFailure": {"@id": "bfe:observesFailure", "@type": "@id"},
    "bfe:observesInterruption": {"@id": "bfe:observesInterruption", "@type": "@id"},
    "bfe:observesOpenBoundary": {"@id": "bfe:observesOpenBoundary", "@type": "@id"},
    "bfe:boundaryInArtifact": {"@id": "bfe:boundaryInArtifact", "@type": "@id"},
    "bfe:entryFirstFailure": {"@id": "bfe:entryFirstFailure", "@type": "@id"},
    "bfe:entryFirstInterruption": {"@id": "bfe:entryFirstInterruption", "@type": "@id"},
    "bfe:candidateInObject": {"@id": "bfe:candidateInObject", "@type": "@id"},
    "bfe:candidateIdentityBasis": {"@id": "bfe:candidateIdentityBasis", "@type": "@id"},
    "bfe:candidateAddressSpace": {"@id": "bfe:candidateAddressSpace", "@type": "@id"},
    "bfe:contentDigest": "bfe:contentDigest",
    "bfe:identifier": "bfe:identifier",
    "bfe:targetVersion": "bfe:targetVersion",
    "bfe:distributionRevision": "bfe:distributionRevision",
    "bfe:targetBuildConfiguration": "bfe:targetBuildConfiguration",
    "bfe:targetPlatform": "bfe:targetPlatform",
    "bfe:interpreterImplementation": "bfe:interpreterImplementation",
    "bfe:candidateAliasIdentifier": "bfe:candidateAliasIdentifier",
    "bfe:toolName": "bfe:toolName",
    "bfe:revision": "bfe:revision",
    "bfe:inventoryDescription": "bfe:inventoryDescription",
    "bfe:candidateAddressValue": {"@id": "bfe:candidateAddressValue", "@type": "xsd:nonNegativeInteger"},
    "bfe:declaredExtentBytes": {"@id": "bfe:declaredExtentBytes", "@type": "xsd:nonNegativeInteger"},
    "bfe:failureStage": "bfe:failureStage",
    "bfe:failureCode": "bfe:failureCode",
    "bfe:diagnosticText": "bfe:diagnosticText",
    "bfe:interruptionKind": "bfe:interruptionKind",
    "bfe:boundaryKind": "bfe:boundaryKind",
    "bfe:boundaryTarget": "bfe:boundaryTarget",
}

DISPOSITION_IRIS = {
    "extracted": BFE + "Extracted",
    "failed": BFE + "Failed",
    "incomplete": BFE + "Incomplete",
    "not_attempted": BFE + "NotAttempted",
}

SAMPLE_POLICY = "sha256-rank-round-half-up-v1"

_LOGGER = logging.getLogger(__name__)
_COMPLETION_OUTCOMES = {
    "extracted": "OK",
    "failed": "FAIL",
    "incomplete": "INCOMPLETE",
    "not_attempted": "SKIP",
}


def _configure_logging() -> None:
    _LOGGER.setLevel(logging.INFO)
    if not _LOGGER.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        )
        formatter.converter = time.gmtime
        handler.setFormatter(formatter)
        _LOGGER.addHandler(handler)
        _LOGGER.propagate = False


def _log_candidate_completion(
    candidate: dict[str, Any], disposition: str, completed: int, total: int
) -> None:
    _LOGGER.info(
        "%s function=%r candidate=%s completed=%d/%d",
        _COMPLETION_OUTCOMES[disposition],
        candidate["symbol"],
        candidate["id"],
        completed,
        total,
    )


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_version(distribution: str) -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _slug(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-")


def _tool_release(name: str, revision: str) -> tuple[str, dict[str, Any]]:
    identifier = f"urn:wruh:tool:{_slug(name)}:{_slug(revision)}"
    return identifier, {
        "@id": identifier,
        "@type": "bfe:ToolRelease",
        "bfe:toolName": name,
        "bfe:revision": revision,
    }


def _explicit_build_value(arguments: argparse.Namespace, name: str) -> str | None:
    value = getattr(arguments, name, None)
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized if normalized and normalized.lower() != "unknown" else None


def _build_provenance(
    arguments: argparse.Namespace,
    *,
    census_id: str,
    image_id: str,
    binary_id: str,
    target_release_id: str,
) -> tuple[dict[str, str], list[tuple[str, dict[str, Any]]], dict[str, Any] | None]:
    build_package = _explicit_build_value(arguments, "build_package")
    build_output = _explicit_build_value(arguments, "build_output")
    nixpkgs_revision = _explicit_build_value(arguments, "nixpkgs_revision")
    nix_version = _explicit_build_value(arguments, "nix_version")
    build_configuration = _explicit_build_value(arguments, "build_configuration")

    image_properties: dict[str, str] = {}
    if nixpkgs_revision:
        image_properties["bfe:distributionRevision"] = nixpkgs_revision
    if build_configuration:
        image_properties["bfe:targetBuildConfiguration"] = build_configuration

    build_tool_releases: list[tuple[str, dict[str, Any]]] = []
    build_node = None
    if build_package and build_output:
        build_node = {
            "@id": f"{census_id}/build",
            "@type": "bfe:BuildActivity",
            "bfe:buildGeneratesBinaryObject": {"@id": binary_id},
            "bfe:buildGeneratesImage": {"@id": image_id},
            "bfe:buildGeneratesToolRelease": {"@id": target_release_id},
            "bfe:identifier": [build_package, build_output],
        }
        if nixpkgs_revision:
            nixpkgs_id, nixpkgs_node = _tool_release("Nixpkgs", nixpkgs_revision)
            build_tool_releases.append((nixpkgs_id, nixpkgs_node))
            build_node["bfe:buildUsesInput"] = [{"@id": nixpkgs_id}]
        if nix_version:
            nix_id, nix_node = _tool_release("Nix", nix_version)
            build_tool_releases.append((nix_id, nix_node))
            build_node["bfe:activityUsesToolRelease"] = {"@id": nix_id}

    return image_properties, build_tool_releases, build_node


def _function_candidates(project: Any) -> list[dict[str, Any]]:
    image = project.loader.main_object
    grouped: dict[int, list[Any]] = {}
    for symbol in image.symbols:
        if (
            not getattr(symbol, "name", "")
            or int(getattr(symbol, "size", 0)) <= 0
            or getattr(getattr(symbol, "type", None), "name", "") != "TYPE_FUNCTION"
            or getattr(symbol, "is_import", False)
        ):
            continue
        grouped.setdefault(int(symbol.rebased_addr), []).append(symbol)

    candidates: list[dict[str, Any]] = []
    for rebased_address, aliases in sorted(grouped.items()):
        aliases.sort(key=lambda symbol: (-int(symbol.size), str(symbol.name)))
        primary = aliases[0]
        relative_address = int(getattr(primary, "relative_addr", rebased_address - int(image.mapped_base)))
        linked_address = getattr(primary, "linked_addr", None)
        if linked_address is None:
            linked_address = int(getattr(image, "linked_base", 0)) + relative_address
        names = sorted({str(symbol.name) for symbol in aliases})
        candidates.append({
            "id": f"fn_{relative_address:016x}",
            "address": rebased_address,
            "relative_address": relative_address,
            "object_virtual_address": int(linked_address),
            "size": int(primary.size),
            "symbol": str(primary.name),
            "aliases": names,
        })
    return candidates


def _sample_percentage(value: str) -> Decimal:
    try:
        percentage = Decimal(value)
    except InvalidOperation as error:
        raise argparse.ArgumentTypeError("sample percentage must be a decimal number") from error
    if not percentage.is_finite() or percentage < 0 or percentage > 100:
        raise argparse.ArgumentTypeError("sample percentage must be finite and between 0 and 100, inclusive")
    return percentage


def _select_candidates(
    candidates: list[dict[str, Any]],
    binary_digest: str,
    seed: str | None,
    percentage: Decimal | None,
    only_symbols: Sequence[str] | None = None,
) -> tuple[set[str], dict[str, Any]]:
    if only_symbols:
        if seed is not None or percentage is not None:
            raise ValueError("explicit symbol selection cannot be combined with sampling")
        requested_symbols = sorted(set(only_symbols))
        matches = {symbol: set() for symbol in requested_symbols}
        for candidate in candidates:
            for symbol in candidate.get("aliases", [candidate["symbol"]]):
                if symbol in matches:
                    matches[symbol].add(candidate["id"])
        missing = [symbol for symbol, ids in matches.items() if not ids]
        ambiguous = {
            symbol: sorted(ids)
            for symbol, ids in matches.items()
            if len(ids) > 1
        }
        if missing or ambiguous:
            problems = []
            if missing:
                problems.append(f"unknown symbols={missing}")
            if ambiguous:
                problems.append(f"ambiguous symbols={ambiguous}")
            raise ValueError("cannot select census symbols: " + "; ".join(problems))
        selected_ids = {next(iter(ids)) for ids in matches.values()}
        return selected_ids, {
            "seed": None,
            "requestedPercentage": None,
            "selectedCount": len(selected_ids),
            "samplingPolicy": "explicit-symbols-v1",
            "selectedSymbols": requested_symbols,
        }

    if seed is None or percentage is None:
        return {candidate["id"] for candidate in candidates}, {
            "seed": None,
            "requestedPercentage": None,
            "selectedCount": len(candidates),
            "samplingPolicy": "full-census-v1",
        }

    exact_count = Fraction(len(candidates)) * Fraction(percentage) / 100
    selected_count = (2 * exact_count.numerator + exact_count.denominator) // (2 * exact_count.denominator)
    seed_bytes = seed.encode("utf-8")
    binary_bytes = bytes.fromhex(binary_digest)
    ranked: list[tuple[bytes, str]] = []
    for candidate in candidates:
        candidate_id = candidate["id"]
        candidate_bytes = candidate_id.encode("utf-8")
        payload = bytearray(b"wruh-binary-census-sample-v1\0")
        payload.extend(len(seed_bytes).to_bytes(8, "big"))
        payload.extend(seed_bytes)
        payload.extend(binary_bytes)
        payload.extend(len(candidate_bytes).to_bytes(8, "big"))
        payload.extend(candidate_bytes)
        ranked.append((hashlib.sha256(payload).digest(), candidate_id))

    selected_ids = {candidate_id for _, candidate_id in sorted(ranked)[:selected_count]}
    return selected_ids, {
        "seed": seed,
        "requestedPercentage": str(percentage),
        "selectedCount": selected_count,
        "samplingPolicy": SAMPLE_POLICY,
    }


def _candidate_manifest(
    project: Any,
    binary_digest: str,
    object_path: Path,
    object_digest: str,
    candidate: dict[str, Any],
) -> dict[str, Any]:
    image = project.loader.main_object
    root = {
        "address": candidate["address"],
        "size": candidate["size"],
        "symbol": candidate["symbol"],
        "image_sha256": object_digest,
        "object_path": str(object_path),
    }
    return {
        "arch": project.arch.name,
        "bits": project.arch.bits,
        "call_graph": {candidate["id"]: {}},
        "image_sha256": binary_digest,
        "indirect_jumps": {},
        "pic": bool(image.pic),
        "primitive_boundaries": {},
        "roots": {candidate["id"]: root},
        "schema": 1,
        "open_transfers": True,
    }


def _entry_nodes(
    *,
    census_id: str,
    candidate: dict[str, Any],
    binary_id: str,
    disposition: str,
    attempt_id: str | None,
    started: str | None,
    ended: str | None,
    tool_release_ids: list[str],
    failure: dict[str, str] | None = None,
    artifact_member: str | None = None,
    artifact_digest: str | None = None,
    open_calls: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    candidate_id = f"{census_id}/candidate/{candidate['id']}"
    entry_id = f"{census_id}/entry/{candidate['id']}"
    nodes: list[dict[str, Any]] = [{
        "@id": candidate_id,
        "@type": "bfe:FunctionCandidate",
        "bfe:candidateInObject": {"@id": binary_id},
        "bfe:candidateIdentityBasis": [
            {"@id": "bfe:SizedSymbol"},
            {"@id": "bfe:UniqueEntryAddress"},
        ],
        "bfe:candidateAddressSpace": {"@id": "bfe:ObjectVirtualAddress"},
        "bfe:candidateAddressValue": candidate["object_virtual_address"],
        "bfe:declaredExtentBytes": candidate["size"],
        "bfe:candidateAliasIdentifier": candidate["aliases"],
    }]
    attempt_node: dict[str, Any] | None = None
    if attempt_id is not None:
        attempt_node = {
            "@id": attempt_id,
            "@type": "bfe:FunctionExtractionAttempt",
            "bfe:attemptsCandidate": {"@id": candidate_id},
            "bfe:activityUsesToolRelease": [{"@id": identifier} for identifier in tool_release_ids],
            "prov:startedAtTime": started,
            "prov:endedAtTime": ended,
        }
        nodes.append(attempt_node)
    entry: dict[str, Any] = {
        "@id": entry_id,
        "@type": "bfe:CensusEntry",
        "bfe:entryRecordsCandidate": {"@id": candidate_id},
        "bfe:entryDisposition": {"@id": DISPOSITION_IRIS[disposition]},
    }
    if attempt_id is not None:
        entry["bfe:entryHasAttempt"] = {"@id": attempt_id}

    if failure is not None:
        if attempt_node is None or attempt_id is None:
            raise ValueError("failure observations require an extraction attempt")
        observation_id = f"{attempt_id}/observation"
        if disposition == "incomplete":
            node = {
                "@id": observation_id,
                "@type": "bfe:InterruptionObservation",
                "bfe:interruptionKind": f"{failure['code']} during {failure['stage']}",
                "bfe:diagnosticText": failure["message"],
            }
            attempt_node["bfe:observesInterruption"] = {"@id": observation_id}
            entry["bfe:entryFirstInterruption"] = {"@id": observation_id}
        else:
            node = {
                "@id": observation_id,
                "@type": "bfe:FailureObservation",
                "bfe:failureStage": failure["stage"],
                "bfe:failureCode": failure["code"],
                "bfe:diagnosticText": failure["message"],
            }
            attempt_node["bfe:observesFailure"] = {"@id": observation_id}
            entry["bfe:entryFirstFailure"] = {"@id": observation_id}
        nodes.append(node)

    if artifact_member is not None and artifact_digest is not None:
        if attempt_node is None or attempt_id is None:
            raise ValueError("extraction artifacts require an extraction attempt")
        artifact_id = f"{census_id}/artifact/{candidate['id']}"
        nodes.append({
            "@id": artifact_id,
            "@type": "bfe:ExtractionArtifact",
            "bfe:identifier": artifact_member,
            "bfe:contentDigest": f"sha256:{artifact_digest}",
            "prov:wasGeneratedBy": {"@id": attempt_id},
        })
        attempt_node["bfe:generatesArtifact"] = {"@id": artifact_id}

        for index, call in enumerate(open_calls or []):
            observation_id = f"{attempt_id}/open-boundary/{index}"
            nodes.append({
                "@id": observation_id,
                "@type": "bfe:OpenBoundaryObservation",
                "bfe:boundaryKind": call.get("kind", "call"),
                "bfe:boundaryTarget": call.get("name", "unknown"),
                "bfe:boundaryInArtifact": {"@id": artifact_id},
            })
            attempt_node.setdefault("bfe:observesOpenBoundary", []).append({"@id": observation_id})
    return nodes, entry


def _ci_provenance_nodes(arguments: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if arguments.ci_run_id is None:
        return [], {}

    server_url = arguments.ci_server_url.rstrip("/")
    repository = arguments.ci_repository
    pull_request_number = arguments.ci_pull_request_number
    pull_request_id = arguments.ci_pull_request_id
    run_id = arguments.ci_run_id
    run_attempt = arguments.ci_run_attempt
    head_repository = arguments.ci_pull_request_head_repository or repository
    pull_request_url = f"{server_url}/{repository}/pull/{pull_request_number}"
    run_url = f"{server_url}/{repository}/actions/runs/{run_id}/attempts/{run_attempt}"

    commit_nodes: dict[str, dict[str, Any]] = {}
    commit_references: list[dict[str, str]] = []
    for commit_repository, revision, label in (
        (repository, arguments.ci_checked_out_sha, "Commit checked out by the workflow"),
        (head_repository, arguments.ci_pull_request_head_sha, "Pull request head commit"),
    ):
        commit_url = f"{server_url}/{commit_repository}/commit/{revision}"
        commit_node = commit_nodes.get(commit_url)
        if commit_node is None:
            commit_node = {
                "@id": commit_url,
                "@type": "prov:Entity",
                "bfe:identifier": f"git-commit:{revision}",
                "rdfs:label": label,
            }
            commit_nodes[commit_url] = commit_node
            commit_references.append({"@id": commit_url})
        elif label not in commit_node["rdfs:label"]:
            commit_node["rdfs:label"] = [commit_node["rdfs:label"], label]

    pull_request_node = {
        "@id": pull_request_url,
        "@type": "prov:Entity",
        "bfe:identifier": [
            f"github-pull-request-number:{pull_request_number}",
            f"github-pull-request-id:{pull_request_id}",
        ],
        "rdfs:label": f"GitHub pull request #{pull_request_number}",
    }
    run_node = {
        "@id": run_url,
        "@type": "prov:Activity",
        "bfe:identifier": f"github-actions-run:{run_id}/attempt/{run_attempt}",
        "rdfs:label": f"GitHub Actions workflow {arguments.ci_workflow}, job {arguments.ci_job}",
        "prov:used": [
            {"@id": pull_request_url},
            *commit_references,
        ],
    }
    census_properties = {
        "prov:wasInformedBy": {"@id": run_url},
        "prov:used": [
            {"@id": pull_request_url},
            *commit_references,
        ],
    }
    return [pull_request_node, *commit_nodes.values(), run_node], census_properties


def _write_jsonld_report(report_path: Path, graph: list[dict[str, Any]]) -> None:
    report_path.write_text(
        json.dumps({"@context": JSONLD_CONTEXT, "@graph": graph}, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _write_report(
    *,
    output_dir: Path,
    graph: list[dict[str, Any]],
    census_id: str,
    target_id: str,
    binary_digest: str,
    counts: Counter[str],
    failures: Counter[str],
    total: int,
    started: str,
    ended: str,
    artifact_path: Path,
    interrupted: bool,
    sampling: dict[str, Any],
) -> None:
    census_node = next(node for node in graph if node.get("@id") == census_id)
    census_node["prov:endedAtTime"] = ended
    report_path = output_dir / "census.jsonld"
    _write_jsonld_report(report_path, graph)
    artifact_digest = _sha256(artifact_path) if artifact_path.exists() else None
    summary = {
        "schema": "wruh-binary-function-census-summary-v1",
        "targetId": target_id,
        "binarySha256": binary_digest,
        "startedAt": started,
        "endedAt": ended,
        "inventoryCandidates": total,
        "attempted": sum(count for disposition, count in counts.items() if disposition != "not_attempted"),
        "dispositions": dict(sorted(counts.items())),
        "sampling": sampling,
        "failureCategories": dict(sorted(failures.items())),
        "artifactArchive": str(artifact_path.name),
        "artifactArchiveSha256": artifact_digest,
        "reportSha256": _sha256(report_path),
        "interrupted": interrupted,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _write_progress(
    output_dir: Path,
    *,
    target_id: str,
    binary_digest: str,
    total: int,
    completed: int,
    counts: Counter[str],
    failures: Counter[str],
    sampling: dict[str, Any],
    interrupted: bool = False,
) -> None:
    payload = {
        "schema": "wruh-binary-function-census-progress-v1",
        "targetId": target_id,
        "binarySha256": binary_digest,
        "inventoryCandidates": total,
        "completed": completed,
        "dispositions": dict(sorted(counts.items())),
        "failureCategories": dict(sorted(failures.items())),
        "sampling": sampling,
        "interrupted": interrupted,
        "updatedAt": _now(),
    }
    temporary = output_dir / "progress.json.tmp"
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output_dir / "progress.json")


def _write_global_failure(
    output_dir: Path,
    target_id: str,
    binary_identifier: str,
    stage: str,
    error: Exception,
    *,
    ci_run_id: int | None = None,
    ci_run_attempt: int | None = None,
    ci_checked_out_sha: str | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema": "wruh-binary-function-census-summary-v1",
        "targetId": target_id,
        "binary": binary_identifier,
        "inventoryCandidates": 0,
        "attempted": 0,
        "dispositions": {},
        "failureCategories": {f"{stage}:{type(error).__name__}": 1},
        "globalFailure": {"stage": stage, "code": type(error).__name__, "message": str(error)[:2000]},
    }
    if ci_run_id is not None and ci_run_attempt is not None and ci_checked_out_sha:
        summary["provenance"] = {
            "run": f"github-actions-run:{ci_run_id}/attempt/{ci_run_attempt}",
            "revision": f"git-commit:{ci_checked_out_sha}",
        }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(arguments: argparse.Namespace) -> int:
    from extractor.native_runtime import preload_libstdcxx

    preload_libstdcxx()

    import angr

    from extractor.amd64_state import clear_smt_translation_cache
    from extractor.binary_cfg import build_static_cfg
    from extractor.binary_inventory import PinnedBinary
    from extractor.fresh import extract_fresh_function

    binary = arguments.binary.resolve(strict=True)
    binary_identifier = arguments.binary_identifier or str(binary)
    output_dir = arguments.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    binary_digest = _sha256(binary)
    started = _now()

    try:
        project = angr.Project(str(binary), auto_load_libs=False)
        if project.arch.name != "AMD64" or project.arch.bits != 64:
            raise RuntimeError(f"unsupported architecture: {project.arch.name}/{project.arch.bits}")
        image = project.loader.main_object
        object_path = Path(str(image.binary)).resolve()
        candidates = _function_candidates(project)
    except Exception as error:  # noqa: BLE001 -- record an inventory-generation failure in the report
        _write_global_failure(
            output_dir,
            arguments.target_id,
            binary_identifier,
            "inventory-generation",
            error,
            ci_run_id=arguments.ci_run_id,
            ci_run_attempt=arguments.ci_run_attempt,
            ci_checked_out_sha=arguments.ci_checked_out_sha,
        )
        print(f"inventory-generation failed: {type(error).__name__}: {error}")
        return 2

    selected_candidate_ids, sampling = _select_candidates(
        candidates,
        binary_digest,
        arguments.sample_seed,
        arguments.sample_percentage,
        arguments.only_symbol,
    )

    run_id = uuid.uuid4().hex
    census_id = f"urn:wruh:census:{_slug(arguments.target_id)}:{binary_digest[:16]}:{run_id}"
    image_id = f"urn:wruh:image:sha256:{binary_digest}"
    binary_id = f"urn:wruh:binary:sha256:{binary_digest}"
    inventory_id = f"{census_id}/inventory"
    policy_id = f"{census_id}/inventory-policy"
    inventory_activity_id = f"{census_id}/inventory-generation"
    census_started = started
    graph: list[dict[str, Any]] = []
    object_digest = _sha256(object_path)

    tool_releases = [
        _tool_release("angr", _safe_version("angr")),
        _tool_release("WRUH", arguments.wruh_revision),
        _tool_release("AYXG", arguments.ayxg_revision),
        _tool_release("Python", platform.python_version()),
        _tool_release("z3-solver", _safe_version("z3-solver")),
        _tool_release("capstone", _safe_version("capstone")),
        _tool_release("pyvex", _safe_version("pyvex")),
        _tool_release("Bazel", arguments.bazel_version),
    ]
    target_release_id, target_release = _tool_release(
        arguments.target_implementation or arguments.target_id,
        arguments.target_version,
    )
    build_image_properties, build_tool_releases, build_node = _build_provenance(
        arguments,
        census_id=census_id,
        image_id=image_id,
        binary_id=binary_id,
        target_release_id=target_release_id,
    )
    tool_releases.extend(build_tool_releases)
    graph.extend(node for _, node in tool_releases)
    graph.append(target_release)
    tool_ids = [identifier for identifier, _ in tool_releases]
    census_node = {
        "@id": census_id,
        "@type": "bfe:ExtractionCensus",
        "bfe:censusUsesImage": {"@id": image_id},
        "bfe:censusUsesInventory": {"@id": inventory_id},
        "bfe:censusGeneratesEntry": [],
        "bfe:activityUsesToolRelease": [{"@id": identifier} for identifier in tool_ids[:8]],
        "prov:startedAtTime": census_started,
    }
    ci_nodes, ci_census_properties = _ci_provenance_nodes(arguments)
    census_node.update(ci_census_properties)
    inventory_activity_node = {
        "@id": inventory_activity_id,
        "@type": "bfe:InventoryGeneration",
        "bfe:inventoryGenerationUsesImage": {"@id": image_id},
        "bfe:inventoryGenerationUsesPolicy": {"@id": policy_id},
        "bfe:generatesInventory": {"@id": inventory_id},
        "bfe:inventoryGenerationUsesToolRelease": [{"@id": identifier} for identifier in tool_ids[:7]],
        "prov:startedAtTime": census_started,
    }
    graph.extend(ci_nodes)
    graph.extend([
        {
            "@id": binary_id,
            "@type": "bfe:BinaryObject",
            "bfe:identifier": binary_identifier,
            "bfe:contentDigest": f"sha256:{binary_digest}",
        },
        {
            "@id": image_id,
            "@type": "bfe:InterpreterImage" if arguments.target_kind == "interpreter" else "bfe:AnalyzedImage",
            "bfe:hasBinaryObject": {"@id": binary_id},
            "bfe:targetVersion": arguments.target_version,
            "bfe:targetPlatform": arguments.target_platform,
            **build_image_properties,
            **({"bfe:interpreterImplementation": arguments.target_implementation} if arguments.target_kind == "interpreter" else {}),
        },
        *([build_node] if build_node is not None else []),
        {
            "@id": policy_id,
            "@type": "bfe:InventoryPolicy",
            "bfe:inventoryDescription": (
                "Enumerate defined, sized ELF function symbols in the main object; "
                "coalesce aliases by rebased entry address; select the largest declared "
                "extent and then the lexically first symbol name; retain all alias names. "
                "Candidates are keyed by the object's relative virtual address."
            ),
        },
        {
            "@id": inventory_id,
            "@type": "bfe:FunctionInventory",
            "prov:hadMember": [
                {"@id": f"{census_id}/candidate/{candidate['id']}"}
                for candidate in candidates
            ],
        },
        inventory_activity_node,
        census_node,
    ])

    counts: Counter[str] = Counter()
    failure_categories: Counter[str] = Counter()
    archive_path = output_dir / "function-artifacts.tar.gz"
    entries_path = output_dir / "entries.jsonl"
    interrupted = False
    _write_progress(
        output_dir,
        target_id=arguments.target_id,
        binary_digest=binary_digest,
        total=len(candidates),
        completed=0,
        counts=counts,
        failures=failure_categories,
        sampling=sampling,
    )

    with (
        entries_path.open("w", encoding="utf-8") as ledger,
        archive_path.open("wb") as raw_archive,
        gzip.GzipFile(filename="", mode="wb", fileobj=raw_archive, mtime=0) as compressed,
        tarfile.open(fileobj=compressed, mode="w|") as archive,
    ):
        for index, candidate in enumerate(candidates):
            candidate_id = f"{census_id}/candidate/{candidate['id']}"
            entry_id = f"{census_id}/entry/{candidate['id']}"
            selected = candidate["id"] in selected_candidate_ids
            attempt_id = f"{census_id}/attempt/{candidate['id']}/1" if selected else None
            attempt_started = _now() if selected else None
            disposition = "failed" if selected else "not_attempted"
            failure: dict[str, str] | None = None
            artifact_member: str | None = None
            artifact_digest: str | None = None
            open_calls: list[dict[str, Any]] = []
            stage = "inventory"
            if selected:
                try:
                    manifest = _candidate_manifest(
                        project, binary_digest, object_path, object_digest, candidate
                    )
                    pinned = PinnedBinary(binary, manifest, project)
                    stage = "cfg"
                    cfg = build_static_cfg(pinned)
                    stage = "extraction"
                    fresh = extract_fresh_function(pinned, cfg, candidate["id"])
                    model = fresh.canonical_json()
                    artifact_digest = hashlib.sha256(model).hexdigest()
                    artifact_member = f"functions/{candidate['relative_address']:016x}.json"
                    info = tarfile.TarInfo(artifact_member)
                    info.size = len(model)
                    info.mtime = 0
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    archive.addfile(info, io.BytesIO(model))
                    open_calls = [
                        call for call in cfg["roots"][candidate["id"]].get("calls", [])
                        if call.get("kind") == "open"
                    ]
                    disposition = "extracted"
                except (MemoryError, TimeoutError) as error:
                    disposition = "incomplete"
                    failure = {
                        "stage": stage,
                        "code": type(error).__name__,
                        "message": str(error)[:2000],
                    }
                except Exception as error:  # noqa: BLE001 -- record this candidate failure and continue
                    disposition = "failed"
                    failure = {
                        "stage": stage,
                        "code": type(error).__name__,
                        "message": str(error)[:2000],
                    }
                except KeyboardInterrupt:
                    disposition = "incomplete"
                    interrupted = True
                    failure = {
                        "stage": stage,
                        "code": "KeyboardInterrupt",
                        "message": "census interrupted by user or runner",
                    }

            attempt_ended = _now() if selected else None
            counts[disposition] += 1
            if failure:
                failure_categories[f"{failure['stage']}:{failure['code']}"] += 1
            nodes, entry = _entry_nodes(
                census_id=census_id,
                candidate=candidate,
                binary_id=binary_id,
                disposition=disposition,
                attempt_id=attempt_id,
                started=attempt_started,
                ended=attempt_ended,
                tool_release_ids=tool_ids[:7],
                failure=failure,
                artifact_member=artifact_member,
                artifact_digest=artifact_digest,
                open_calls=open_calls,
            )
            graph.extend(nodes)
            graph.append(entry)
            census_node["bfe:censusGeneratesEntry"].append({"@id": entry_id})
            ledger.write(json.dumps({
                "index": index,
                "candidate": candidate_id,
                "entry": entry_id,
                "symbol": candidate["symbol"],
                "relativeAddress": candidate["relative_address"],
                "attempt": attempt_id,
                "disposition": disposition,
                "failureStage": failure["stage"] if failure else None,
                "failureCode": failure["code"] if failure else None,
                "artifact": artifact_member,
            }, sort_keys=True) + "\n")
            ledger.flush()
            _log_candidate_completion(
                candidate,
                disposition,
                completed=sum(counts.values()),
                total=len(candidates),
            )
            if (index + 1) % 100 == 0:
                _write_progress(
                    output_dir,
                    target_id=arguments.target_id,
                    binary_digest=binary_digest,
                    total=len(candidates),
                    completed=index + 1,
                    counts=counts,
                    failures=failure_categories,
                    sampling=sampling,
                )
            # The extractor keeps an unbounded Angr-to-Z3 AST memo.
            # Its entries are local to one function and must not make
            # a long census grow with the number of candidates.
            clear_smt_translation_cache()
            if (index + 1) % 100 == 0:
                gc.collect()
            if interrupted:
                break
    ended = _now()
    inventory_activity_node["prov:endedAtTime"] = ended
    _write_progress(
        output_dir,
        target_id=arguments.target_id,
        binary_digest=binary_digest,
        total=len(candidates),
        completed=sum(counts.values()),
        counts=counts,
        failures=failure_categories,
        sampling=sampling,
        interrupted=interrupted,
    )
    _write_report(
        output_dir=output_dir,
        graph=graph,
        census_id=census_id,
        target_id=arguments.target_id,
        binary_digest=binary_digest,
        counts=counts,
        failures=failure_categories,
        total=len(candidates),
        started=started,
        ended=ended,
        artifact_path=archive_path,
        interrupted=interrupted,
        sampling=sampling,
    )
    print(json.dumps({
        "target": arguments.target_id,
        "binarySha256": binary_digest,
        "inventoryCandidates": len(candidates),
        "dispositions": dict(sorted(counts.items())),
        "sampling": sampling,
        "failureCategories": dict(sorted(failure_categories.items())),
        "report": str(output_dir / "census.jsonld"),
        "summary": str(output_dir / "summary.json"),
    }, sort_keys=True))
    return 130 if interrupted else 0


_GITHUB_ACTIONS_RUNNER_MARKERS = (
    "GITHUB_RUN_ID",
    "GITHUB_RUN_ATTEMPT",
    "GITHUB_EVENT_PATH",
    "GITHUB_REPOSITORY",
    "GITHUB_SHA",
    "GITHUB_WORKFLOW",
    "GITHUB_JOB",
    "RUNNER_TEMP",
    "RUNNER_OS",
)


def _is_github_actions_runner(environ: Mapping[str, str] | None = None) -> bool:
    environment = os.environ if environ is None else environ
    return environment.get("GITHUB_ACTIONS", "").strip().lower() == "true" or any(
        marker in environment for marker in _GITHUB_ACTIONS_RUNNER_MARKERS
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract every eligible function symbol into PROV-O / BFE census reports.")
    parser.add_argument("--binary", required=True, type=Path, help="ELF executable or shared object to census")
    parser.add_argument("--binary-identifier", help="stable source path recorded in the report")
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--target-kind", choices=("generic", "interpreter"), default="generic")
    parser.add_argument("--target-implementation")
    parser.add_argument("--target-version", required=True)
    parser.add_argument("--target-platform", default="x86_64-linux")
    parser.add_argument("--build-package")
    parser.add_argument("--build-configuration", nargs="+")
    parser.add_argument("--build-output")
    parser.add_argument("--nixpkgs-revision")
    parser.add_argument("--wruh-revision", default="unknown")
    parser.add_argument("--ayxg-revision", default="unknown")
    parser.add_argument("--bazel-version", default="unknown")
    parser.add_argument("--nix-version")
    parser.add_argument("--ci-server-url")
    parser.add_argument("--ci-repository")
    parser.add_argument("--ci-pull-request-number", type=int)
    parser.add_argument("--ci-pull-request-id", type=int)
    parser.add_argument("--ci-pull-request-head-repository")
    parser.add_argument("--ci-pull-request-head-sha")
    parser.add_argument("--ci-run-id", type=int)
    parser.add_argument("--ci-run-attempt", type=int)
    parser.add_argument("--ci-checked-out-sha")
    parser.add_argument("--ci-workflow")
    parser.add_argument("--ci-job")
    undeclared_outputs = os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(undeclared_outputs) if undeclared_outputs else None,
        help="report directory (defaults to Bazel's test undeclared-outputs directory)",
    )
    parser.add_argument(
        "--only-symbol",
        action="append",
        default=[],
        help="extract only exact candidate symbol names; may be repeated",
    )
    parser.add_argument("--sample-seed", help="explicit seed for deterministic candidate sampling")
    parser.add_argument(
        "--sample-percentage",
        type=_sample_percentage,
        help="percentage of candidates to sample (0 through 100; requires --sample-seed)",
    )
    arguments = parser.parse_args()
    if arguments.build_configuration is not None:
        arguments.build_configuration = " ".join(arguments.build_configuration)
    if not arguments.binary.is_absolute():
        runfiles_root = os.environ.get("TEST_SRCDIR")
        if runfiles_root:
            arguments.binary = Path(runfiles_root) / arguments.binary
    if arguments.output_dir is None:
        parser.error("--output-dir is required outside a Bazel test")
    ci_metadata = {
        "--ci-server-url": arguments.ci_server_url,
        "--ci-repository": arguments.ci_repository,
        "--ci-pull-request-number": arguments.ci_pull_request_number,
        "--ci-pull-request-id": arguments.ci_pull_request_id,
        "--ci-pull-request-head-repository": arguments.ci_pull_request_head_repository,
        "--ci-pull-request-head-sha": arguments.ci_pull_request_head_sha,
        "--ci-run-id": arguments.ci_run_id,
        "--ci-run-attempt": arguments.ci_run_attempt,
        "--ci-checked-out-sha": arguments.ci_checked_out_sha,
        "--ci-workflow": arguments.ci_workflow,
        "--ci-job": arguments.ci_job,
    }
    ci_supplied = any(value is not None for value in ci_metadata.values())
    github_actions_runner = _is_github_actions_runner()
    if ci_supplied or github_actions_runner:
        missing = [
            name
            for name, value in ci_metadata.items()
            if value is None or (isinstance(value, str) and not value.strip())
        ]
        if missing:
            if github_actions_runner:
                message = "GitHub Actions runner detected; all CI provenance arguments are required"
            else:
                message = "CI provenance arguments must be supplied together"
            parser.error(message + "; missing " + ", ".join(missing))
    if (arguments.sample_seed is None) != (arguments.sample_percentage is None):
        parser.error("--sample-seed and --sample-percentage must be provided together")
    if arguments.only_symbol and arguments.sample_seed is not None:
        parser.error("--only-symbol cannot be combined with deterministic sampling")
    if arguments.target_kind == "interpreter" and not arguments.target_implementation:
        parser.error("--target-implementation is required for interpreter targets")
    _configure_logging()
    return run(arguments)


if __name__ == "__main__":
    raise SystemExit(main())

