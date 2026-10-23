"""Run a per-function census over a pinned binary and emit PROV-O JSON-LD."""

from __future__ import annotations

import argparse
import gc
import gzip
import hashlib
import importlib.metadata
import io
import json
import platform
import tarfile
import uuid
from collections import Counter
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
    "xsd": XSD,
    "prov:used": {"@id": "prov:used", "@type": "@id"},
    "prov:wasGeneratedBy": {"@id": "prov:wasGeneratedBy", "@type": "@id"},
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
        names = sorted({str(symbol.name) for symbol in aliases})
        candidates.append({
            "id": f"fn_{relative_address:016x}",
            "address": rebased_address,
            "relative_address": relative_address,
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
) -> tuple[set[str], dict[str, Any]]:
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
        "bfe:candidateAddressValue": candidate["relative_address"],
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
    report_path.write_text(
        json.dumps({"@context": JSONLD_CONTEXT, "@graph": graph}, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
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


def _write_global_failure(output_dir: Path, target_id: str, binary: Path, stage: str, error: Exception) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema": "wruh-binary-function-census-summary-v1",
        "targetId": target_id,
        "binary": str(binary),
        "inventoryCandidates": 0,
        "attempted": 0,
        "dispositions": {},
        "failureCategories": {f"{stage}:{type(error).__name__}": 1},
        "globalFailure": {"stage": stage, "code": type(error).__name__, "message": str(error)[:2000]},
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
        _write_global_failure(output_dir, arguments.target_id, binary, "inventory-generation", error)
        print(f"inventory-generation failed: {type(error).__name__}: {error}")
        return 2

    selected_candidate_ids, sampling = _select_candidates(
        candidates,
        binary_digest,
        arguments.sample_seed,
        arguments.sample_percentage,
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
        _tool_release("Nix", arguments.nix_version),
        _tool_release("Nixpkgs", arguments.nixpkgs_revision),
    ]
    target_release_id, target_release = _tool_release(
        arguments.target_implementation or arguments.target_id,
        arguments.target_version,
    )
    graph.extend(node for _, node in tool_releases)
    graph.append(target_release)
    tool_ids = [identifier for identifier, _ in tool_releases]
    build_id = f"{census_id}/build"
    census_node = {
        "@id": census_id,
        "@type": "bfe:ExtractionCensus",
        "bfe:censusUsesImage": {"@id": image_id},
        "bfe:censusUsesInventory": {"@id": inventory_id},
        "bfe:censusGeneratesEntry": [],
        "bfe:activityUsesToolRelease": [{"@id": identifier} for identifier in tool_ids[:8]],
        "prov:startedAtTime": census_started,
    }
    inventory_activity_node = {
        "@id": inventory_activity_id,
        "@type": "bfe:InventoryGeneration",
        "bfe:inventoryGenerationUsesImage": {"@id": image_id},
        "bfe:inventoryGenerationUsesPolicy": {"@id": policy_id},
        "bfe:generatesInventory": {"@id": inventory_id},
        "bfe:inventoryGenerationUsesToolRelease": [{"@id": identifier} for identifier in tool_ids[:7]],
        "prov:startedAtTime": census_started,
    }
    graph.extend([
        {
            "@id": binary_id,
            "@type": "bfe:BinaryObject",
            "bfe:identifier": str(binary),
            "bfe:contentDigest": f"sha256:{binary_digest}",
        },
        {
            "@id": image_id,
            "@type": "bfe:InterpreterImage" if arguments.target_kind == "interpreter" else "bfe:AnalyzedImage",
            "bfe:hasBinaryObject": {"@id": binary_id},
            "bfe:targetVersion": arguments.target_version,
            "bfe:distributionRevision": arguments.nixpkgs_revision,
            "bfe:targetBuildConfiguration": arguments.build_configuration,
            "bfe:targetPlatform": arguments.target_platform,
            **({"bfe:interpreterImplementation": arguments.target_implementation} if arguments.target_kind == "interpreter" else {}),
        },
        {
            "@id": build_id,
            "@type": "bfe:BuildActivity",
            "bfe:buildUsesInput": [{"@id": tool_ids[-1]}],
            "bfe:buildGeneratesBinaryObject": {"@id": binary_id},
            "bfe:buildGeneratesImage": {"@id": image_id},
            "bfe:buildGeneratesToolRelease": {"@id": target_release_id},
            "bfe:activityUsesToolRelease": {"@id": tool_ids[-2]},
            "bfe:identifier": [arguments.build_package, arguments.build_output],
        },
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
            if (index + 1) % 100 == 0:
                print(f"census progress: {index + 1}/{len(candidates)} candidates")
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract every eligible function symbol into PROV-O / BFE census reports.")
    parser.add_argument("--binary", required=True, type=Path, help="ELF executable or shared object to census")
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--target-kind", choices=("generic", "interpreter"), default="generic")
    parser.add_argument("--target-implementation")
    parser.add_argument("--target-version", required=True)
    parser.add_argument("--target-platform", default="x86_64-linux")
    parser.add_argument("--build-package", default="unknown")
    parser.add_argument("--build-configuration", default="unknown")
    parser.add_argument("--build-output", default="unknown")
    parser.add_argument("--nixpkgs-revision", default="unknown")
    parser.add_argument("--wruh-revision", default="unknown")
    parser.add_argument("--ayxg-revision", default="unknown")
    parser.add_argument("--bazel-version", default="unknown")
    parser.add_argument("--nix-version", default="unknown")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--sample-seed", help="explicit seed for deterministic candidate sampling")
    parser.add_argument(
        "--sample-percentage",
        type=_sample_percentage,
        help="percentage of candidates to sample (0 through 100; requires --sample-seed)",
    )
    arguments = parser.parse_args()
    if (arguments.sample_seed is None) != (arguments.sample_percentage is None):
        parser.error("--sample-seed and --sample-percentage must be provided together")
    if arguments.target_kind == "interpreter" and not arguments.target_implementation:
        parser.error("--target-implementation is required for interpreter targets")
    if arguments.build_package == "unknown":
        arguments.build_package = arguments.target_id
    if arguments.build_configuration == "unknown":
        arguments.build_configuration = "Nix package built with symbol tables retained (dontStrip=true)"
    return run(arguments)


if __name__ == "__main__":
    raise SystemExit(main())

