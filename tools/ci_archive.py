#!/usr/bin/env python3
"""First-pass Wruh Actions/PR archive collector.

The process keeps its data root, credentials, runtime, mirror destination, and
schedule in deployment configuration. It uses only the Python standard library.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import gzip
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

API_ROOT = "https://api.github.com"
API_VERSION = "2022-11-28"
PAGE_SIZE = 100
DEFAULT_REPOSITORY = "heartpunk/wruh"
DOCKER_ARTIFACTS = {"wruh-dev-linux-amd64"}
DEFAULT_MAX_RUNS = 100
DEFAULT_API_WORKERS = 3
DEFAULT_DOWNLOAD_WORKERS = 4
DEFAULT_MAX_QPS = 1.0


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_time(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def should_compress(media_type: str, name: str = "", sample: bytes = b"") -> bool:
    media = media_type.lower()
    if "json" in media or media.startswith("text/") or "xml" in media:
        return True
    suffix = Path(name).suffix.lower()
    if suffix in {".json", ".jsonld", ".jsonl", ".txt", ".log", ".xml", ".yaml", ".yml", ".csv"}:
        return True
    if sample and b"\0" not in sample[:4096]:
        try:
            sample[:4096].decode("utf-8")
            return True
        except UnicodeDecodeError:
            return False
    return False


class ArchiveStore:
    def __init__(self, root: Path, min_free_bytes: int = 4 * 1024 * 1024 * 1024):
        self.root = root
        self.min_free_bytes = max(0, min_free_bytes)
        self.objects = root / "objects" / "sha256"
        self.records = root / "records"
        self.temp = root / "tmp"
        for directory in (self.objects, self.records, self.temp, root / "manifests"):
            directory.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(root / "ledger.sqlite3", timeout=60, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=DELETE")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS objects (
                sha256 TEXT PRIMARY KEY,
                relative_path TEXT NOT NULL,
                raw_size INTEGER NOT NULL,
                stored_size INTEGER NOT NULL,
                encoding TEXT NOT NULL,
                media_type TEXT NOT NULL,
                verified_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS runs (
                run_id INTEGER PRIMARY KEY,
                updated_at TEXT,
                status TEXT,
                completed_at TEXT,
                run_attempt INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS job_logs (
                run_id INTEGER NOT NULL,
                attempt INTEGER NOT NULL,
                job_id INTEGER NOT NULL,
                blob_sha256 TEXT,
                status TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                PRIMARY KEY (run_id, attempt, job_id)
            );
            CREATE TABLE IF NOT EXISTS artifacts (
                run_id INTEGER NOT NULL,
                attempt INTEGER NOT NULL,
                artifact_id INTEGER NOT NULL,
                fingerprint TEXT NOT NULL,
                blob_sha256 TEXT,
                status TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                PRIMARY KEY (run_id, attempt, artifact_id, fingerprint)
            );
            """
        )
        self.conn.commit()

    def get_state(self, key: str, default: Any = None) -> Any:
        with self.lock:
            row = self.conn.execute("SELECT value FROM state WHERE key = ?", (key,)).fetchone()
        return default if row is None else json.loads(row[0])

    def set_state(self, key: str, value: Any) -> None:
        with self.lock:
            self.conn.execute(
                "INSERT INTO state(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, json.dumps(value, sort_keys=True)),
            )
            self.conn.commit()

    def event(self, channel: str, value: dict[str, Any]) -> None:
        row = dict(value)
        row.setdefault("observed_at", iso_now())
        encoded = canonical_json(row)
        with self.lock:
            with (self.records / f"{channel}.jsonl.gz").open("ab") as stream:
                with gzip.GzipFile(fileobj=stream, mode="wb", mtime=0, filename="") as zipped:
                    zipped.write(encoded)
                stream.flush()

    def object_path(self, sha256: str, encoding: str) -> Path:
        suffix = ".gz" if encoding == "gzip" else ""
        return self.objects / sha256[:2] / f"{sha256}{suffix}"

    def has_verified(self, sha256: str | None) -> bool:
        if not sha256 or not re.fullmatch(r"[0-9a-f]{64}", sha256):
            return False
        with self.lock:
            row = self.conn.execute(
                "SELECT relative_path, encoding FROM objects WHERE sha256 = ?",
                (sha256,),
            ).fetchone()
        if row is None:
            return False
        return (self.root / row[0]).is_file()

    def put(self, data: bytes, media_type: str, name: str = "", expected_sha256: str | None = None) -> dict[str, Any]:
        sha256 = digest_bytes(data)
        expected = expected_sha256.removeprefix("sha256:").lower() if expected_sha256 else None
        if expected and sha256 != expected:
            raise ValueError(f"GitHub digest mismatch: expected {expected}, got {sha256}")
        compress = should_compress(media_type, name, data)
        encoding = "gzip" if compress else "identity"
        destination = self.object_path(sha256, encoding)
        relative = destination.relative_to(self.root).as_posix()
        with self.lock:
            row = self.conn.execute("SELECT * FROM objects WHERE sha256 = ?", (sha256,)).fetchone()
        if row is not None and (self.root / row[1]).is_file():
            return {
                "sha256": sha256,
                "path": row[1],
                "raw_size": row[2],
                "stored_size": row[3],
                "encoding": row[4],
                "deduplicated": True,
            }

        free_bytes = shutil.disk_usage(self.root).free
        if free_bytes - len(data) < self.min_free_bytes:
            raise OSError(
                f"archive capacity guard: {free_bytes} bytes free; preserving {self.min_free_bytes} bytes"
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix="object-", dir=self.temp)
        try:
            with os.fdopen(fd, "wb") as stream:
                if compress:
                    with gzip.GzipFile(fileobj=stream, mode="wb", mtime=0, filename="") as zipped:
                        zipped.write(data)
                else:
                    stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            stored_size = os.path.getsize(temporary)
            if destination.exists():
                os.unlink(temporary)
            else:
                os.replace(temporary, destination)
            with self.lock:
                self.conn.execute(
                    "INSERT INTO objects(sha256, relative_path, raw_size, stored_size, encoding, media_type, verified_at) "
                    "VALUES(?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(sha256) DO UPDATE SET relative_path=excluded.relative_path, "
                    "raw_size=excluded.raw_size, stored_size=excluded.stored_size, "
                    "encoding=excluded.encoding, media_type=excluded.media_type, verified_at=excluded.verified_at",
                    (sha256, relative, len(data), stored_size, encoding, media_type, iso_now()),
                )
                self.conn.commit()
            self.event("objects", {
                "sha256": sha256,
                "path": relative,
                "raw_size": len(data),
                "stored_size": stored_size,
                "encoding": encoding,
                "media_type": media_type,
            })
            return {
                "sha256": sha256,
                "path": relative,
                "raw_size": len(data),
                "stored_size": stored_size,
                "encoding": encoding,
                "deduplicated": row is not None,
            }
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def put_json(self, data: bytes, source: str) -> dict[str, Any]:
        item = self.put(data, "application/json", name="metadata.json")
        self.event("api-observations", {"source": source, "object_sha256": item["sha256"]})
        return item

    def save_run(self, run: dict[str, Any]) -> None:
        with self.lock:
            self.conn.execute(
                "INSERT INTO runs(run_id, updated_at, status, completed_at, run_attempt) VALUES(?, ?, ?, ?, ?) "
                "ON CONFLICT(run_id) DO UPDATE SET updated_at=excluded.updated_at, status=excluded.status, "
                "completed_at=excluded.completed_at, run_attempt=excluded.run_attempt",
                (
                    run["id"],
                    run.get("updated_at"),
                    run.get("status"),
                    run.get("completed_at"),
                    int(run.get("run_attempt") or 1),
                ),
            )
            self.conn.commit()

    def get_log(self, run_id: int, attempt: int, job_id: int) -> tuple[str | None, str | None]:
        with self.lock:
            row = self.conn.execute(
                "SELECT blob_sha256, status FROM job_logs WHERE run_id=? AND attempt=? AND job_id=?",
                (run_id, attempt, job_id),
            ).fetchone()
        return (None, None) if row is None else (row[0], row[1])

    def set_log(self, run_id: int, attempt: int, job_id: int, blob: str | None, status: str) -> None:
        with self.lock:
            self.conn.execute(
                "INSERT INTO job_logs(run_id, attempt, job_id, blob_sha256, status, observed_at) "
                "VALUES(?, ?, ?, ?, ?, ?) ON CONFLICT(run_id, attempt, job_id) DO UPDATE SET "
                "blob_sha256=excluded.blob_sha256, status=excluded.status, observed_at=excluded.observed_at",
                (run_id, attempt, job_id, blob, status, iso_now()),
            )
            self.conn.commit()

    def get_artifact(
        self, run_id: int, attempt: int, artifact_id: int, fingerprint: str
    ) -> tuple[str | None, str | None]:
        with self.lock:
            row = self.conn.execute(
                "SELECT blob_sha256, status FROM artifacts WHERE run_id=? AND attempt=? AND artifact_id=? AND fingerprint=?",
                (run_id, attempt, artifact_id, fingerprint),
            ).fetchone()
        return (None, None) if row is None else (row[0], row[1])

    def pending_run_ids(self) -> set[int]:
        with self.lock:
            rows = self.conn.execute(
                "SELECT DISTINCT run_id FROM job_logs WHERE status='retry' "
                "UNION SELECT DISTINCT run_id FROM artifacts WHERE status='retry'"
            ).fetchall()
        return {int(row[0]) for row in rows}

    def set_artifact(
        self, run_id: int, attempt: int, artifact_id: int, fingerprint: str, blob: str | None, status: str
    ) -> None:
        with self.lock:
            self.conn.execute(
                "INSERT INTO artifacts(run_id, attempt, artifact_id, fingerprint, blob_sha256, status, observed_at) "
                "VALUES(?, ?, ?, ?, ?, ?, ?) ON CONFLICT(run_id, attempt, artifact_id, fingerprint) DO UPDATE SET "
                "blob_sha256=excluded.blob_sha256, status=excluded.status, observed_at=excluded.observed_at",
                (run_id, attempt, artifact_id, fingerprint, blob, status, iso_now()),
            )
            self.conn.commit()

    def manifest(self, repository: str) -> dict[str, Any]:
        with self.lock:
            object_count, raw_bytes, stored_bytes = self.conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(raw_size), 0), COALESCE(SUM(stored_size), 0) FROM objects"
            ).fetchone()
            run_count = self.conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            log_count = self.conn.execute(
                "SELECT COUNT(*) FROM job_logs WHERE status='stored'"
            ).fetchone()[0]
            artifact_count = self.conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
            stored_artifact_count = self.conn.execute(
                "SELECT COUNT(*) FROM artifacts WHERE status IN ('stored','reused-digest','reused-occurrence','skipped-docker')"
            ).fetchone()[0]
        disk = shutil.disk_usage(self.root)
        return {
            "schema": "wruh-ci-archive-manifest-v1",
            "repository": repository,
            "capacity": {"free_bytes": disk.free, "min_free_bytes": self.min_free_bytes},
            "generated_at": iso_now(),
            "objects": {"unique_count": object_count, "raw_bytes": raw_bytes, "stored_bytes": stored_bytes},
            "actions": {
                "runs_seen": run_count,
                "terminal_job_logs_stored": log_count,
                "artifact_occurrences_seen": artifact_count,
                "artifact_occurrences_resolved_or_skipped": stored_artifact_count,
            },
        }

    def close(self) -> None:
        self.conn.close()


class GitHubError(RuntimeError):
    def __init__(self, status: int, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after


class RateGate:
    def __init__(self, requests_per_second: float):
        self.interval = 1.0 / max(0.05, requests_per_second)
        self.lock = threading.Lock()
        self.next_call = 0.0

    def wait(self) -> None:
        with self.lock:
            now = time.monotonic()
            delay = self.next_call - now
            if delay > 0:
                time.sleep(delay)
                now = time.monotonic()
            self.next_call = max(now, self.next_call) + self.interval


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


class GitHubClient:
    def __init__(self, token_file: Path, store: ArchiveStore, qps: float):
        token = token_file.read_text().strip()
        if not token:
            raise ValueError(f"GitHub token file is empty: {token_file}")
        self.token = token
        self.store = store
        self.gate = RateGate(qps)
        self.opener = urllib.request.build_opener(NoRedirect())

    def _api_request(self, url: str) -> tuple[bytes, Any]:
        self.gate.wait()
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": API_VERSION,
                "User-Agent": "wruh-ci-archive-first-wave",
            },
        )
        try:
            response = self.opener.open(request, timeout=60)
        except urllib.error.HTTPError as error:
            if error.code in (301, 302, 303, 307, 308):
                location = error.headers.get("Location")
                error.close()
                if not location:
                    raise GitHubError(error.code, "redirect response had no Location header")
                # The signed storage URL is a separate host. Do not forward the GitHub token.
                try:
                    response = urllib.request.urlopen(
                        urllib.request.Request(location, headers={"User-Agent": "wruh-ci-archive-first-wave"}),
                        timeout=120,
                    )
                except urllib.error.HTTPError as redirected:
                    retry = redirected.headers.get("Retry-After")
                    raise GitHubError(redirected.code, f"download redirect failed ({redirected.code})",
                                      float(retry) if retry and retry.isdigit() else None) from redirected
            else:
                retry = error.headers.get("Retry-After")
                retry_after = float(retry) if retry and retry.isdigit() else None
                message = f"GitHub API returned HTTP {error.code}"
                if error.code == 403 and error.headers.get("X-RateLimit-Remaining") == "0":
                    reset = error.headers.get("X-RateLimit-Reset")
                    if reset and reset.isdigit():
                        retry_after = max(1.0, float(reset) - time.time())
                    message += " (rate limit exhausted)"
                raise GitHubError(error.code, message, retry_after) from error
        try:
            body = response.read()
            return body, response.headers
        finally:
            response.close()

    def json(self, url_or_path: str) -> tuple[Any, Any, str]:
        url = url_or_path if url_or_path.startswith("https://") else API_ROOT + url_or_path
        body, headers = self._api_request(url)
        data = json.loads(body)
        item = self.store.put_json(body, url)
        return data, headers, item["sha256"]

    def download(self, url: str) -> tuple[bytes, str]:
        body, headers = self._api_request(url)
        return body, headers.get("Content-Type", "application/octet-stream")


class Collector:
    def __init__(
        self,
        repository: str,
        root: Path,
        token_file: Path,
        uvx: str,
        max_runs: int,
        api_workers: int,
        download_workers: int,
        qps: float,
        min_free_bytes: int,
    ):
        self.repository = repository
        self.owner, self.name = repository.split("/", 1)
        self.root = root
        self.token_file = token_file
        self.uvx = uvx
        self.max_runs = max_runs
        self.api_workers = api_workers
        self.download_workers = download_workers
        self.store = ArchiveStore(root, min_free_bytes=min_free_bytes)
        self.api = GitHubClient(token_file, self.store, qps)
        self.repo_api = f"/repos/{self.owner}/{self.name}"
        self.github_backup_dir = Path(os.environ.get("CI_ARCHIVE_GITHUB_BACKUP_DIR", root / "working-github-backup"))
        self.logs_dir = root / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def list_all(self, path: str, key: str | None = None) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        page = 1
        while True:
            separator = "&" if "?" in path else "?"
            url = f"{path}{separator}per_page={PAGE_SIZE}&page={page}"
            data, _, _ = self.api.json(url)
            if isinstance(data, list):
                items = data
            elif key:
                items = data.get(key, [])
            else:
                raise ValueError(f"Expected list response from {url}")
            result.extend(items)
            if len(items) < PAGE_SIZE:
                break
            page += 1
        return result

    def run_github_backup(self, incremental: bool) -> None:
        self.github_backup_dir.mkdir(parents=True, exist_ok=True)
        free_bytes = shutil.disk_usage(self.root).free
        if free_bytes < self.store.min_free_bytes:
            raise OSError(
                f"archive capacity guard: {free_bytes} bytes free; preserving {self.store.min_free_bytes} bytes"
            )
        args = [
            self.uvx, "--from", "github-backup", "github-backup",
            "--token", f"file://{self.token_file}",
            "--output-directory", str(self.github_backup_dir),
            "--repository", self.name,
            "--repositories", "--bare", "--no-prune", "--prefer-ssh",
            "--pulls", "--pull-comments", "--pull-reviews", "--pull-commits",
            "--pull-details", "--issue-comments",
            "--throttle-limit", "1000", "--throttle-pause", "30",
            self.owner,
        ]
        if incremental:
            args.insert(4, "--incremental")
        stamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
        log_path = self.logs_dir / f"github-backup-{stamp}.log"
        with log_path.open("wb") as log:
            result = subprocess.run(
                args,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=3600,
                check=False,
                env=os.environ.copy(),
            )
        compressed_log = log_path.with_suffix(log_path.suffix + ".gz")
        with log_path.open("rb") as source, compressed_log.open("wb") as raw_target:
            with gzip.GzipFile(fileobj=raw_target, mode="wb", mtime=0, filename="") as zipped:
                shutil.copyfileobj(source, zipped)
        log_path.unlink()
        self.store.event("collector", {
            "kind": "github-backup",
            "incremental": incremental,
            "exit_code": result.returncode,
            "log": compressed_log.relative_to(self.root).as_posix(),
        })
        if result.returncode != 0:
            raise RuntimeError(f"github-backup exited {result.returncode}; see {compressed_log}")
        self.store.set_state("github_backup_initialized", True)
        self.import_cli_json()

    def import_cli_json(self) -> None:
        imported = 0
        for path in self.github_backup_dir.rglob("*.json"):
            if ".git" in path.parts or not path.is_file():
                continue
            try:
                data = path.read_bytes()
            except OSError:
                continue
            if len(data) > 64 * 1024 * 1024:
                self.store.event("collector", {
                    "kind": "github-backup-json-too-large",
                    "path": path.relative_to(self.github_backup_dir).as_posix(),
                    "size": len(data),
                })
                continue
            item = self.store.put(data, "application/json", name=path.name)
            self.store.event("pr-snapshots", {
                "source": "github-backup",
                "path": path.relative_to(self.github_backup_dir).as_posix(),
                "object_sha256": item["sha256"],
            })
            imported += 1
        self.store.event("collector", {"kind": "github-backup-json-import", "files_seen": imported})

    def capture_pr(self, pr: dict[str, Any]) -> dict[str, Any]:
        number = int(pr["number"])
        detail, _, detail_sha = self.api.json(f"{self.repo_api}/pulls/{number}")
        self.store.event("pull-requests", {
            "number": number,
            "kind": "details",
            "updated_at": detail.get("updated_at"),
            "object_sha256": detail_sha,
            "api": detail,
        })
        for endpoint, key in (
            (f"{self.repo_api}/pulls/{number}/commits", None),
            (f"{self.repo_api}/pulls/{number}/reviews", None),
            (f"{self.repo_api}/pulls/{number}/comments", None),
            (f"{self.repo_api}/issues/{number}/comments", None),
        ):
            for item in self.list_all(endpoint, key):
                payload = canonical_json(item)
                stored = self.store.put(payload, "application/json", name="pr-record.json")
                self.store.event("pull-requests", {
                    "number": number,
                    "kind": endpoint.rsplit("/", 1)[-1],
                    "item_id": item.get("id") or item.get("sha") or item.get("commit_id"),
                    "object_sha256": stored["sha256"],
                    "api": item,
                })
        self.store.set_state(f"pr:{number}:updated_at", pr.get("updated_at"))
        return detail

    def capture_pr_data(self, force: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
        prs = self.list_all(f"{self.repo_api}/pulls?state=all", None)
        changed = []
        for pr in prs:
            number = int(pr["number"])
            previous = self.store.get_state(f"pr:{number}:updated_at")
            if force or previous != pr.get("updated_at"):
                changed.append(pr)
        if not self.store.get_state("github_backup_initialized", False):
            self.run_github_backup(incremental=False)
        elif changed:
            self.run_github_backup(incremental=True)
        elif force:
            self.run_github_backup(incremental=True)

        details: list[dict[str, Any]] = []
        if changed or force:
            selected = prs if force else changed
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.api_workers) as pool:
                futures = {pool.submit(self.capture_pr, pr): pr for pr in selected}
                for future in concurrent.futures.as_completed(futures):
                    details.append(future.result())
        changed_numbers = {int(pr["number"]) for pr in changed}
        action_links = [detail for detail in details if int(detail["number"]) in changed_numbers]
        return details, action_links, bool(changed or force)

    @staticmethod
    def artifact_fingerprint(artifact: dict[str, Any]) -> str:
        fields = {
            key: artifact.get(key)
            for key in ("id", "name", "size_in_bytes", "created_at", "updated_at", "digest", "expired")
        }
        return digest_bytes(canonical_json(fields))

    @staticmethod
    def skip_artifact(name: str) -> str | None:
        lowered = name.lower()
        if name in DOCKER_ARTIFACTS or ("docker" in lowered and "image" in lowered):
            return "skipped-docker"
        return None

    def download_job_log(self, run: dict[str, Any], attempt: int, job: dict[str, Any]) -> None:
        run_id = int(run["id"])
        job_id = int(job["id"])
        try:
            body, media_type = self.api.download(
                f"{API_ROOT}{self.repo_api}/actions/jobs/{job_id}/logs"
            )
            stored = self.store.put(body, media_type, name=f"job-{job_id}.log")
            self.store.set_log(run_id, attempt, job_id, stored["sha256"], "stored")
            self.store.event("job-logs", {
                "run_id": run_id,
                "attempt": attempt,
                "job_id": job_id,
                "job_name": job.get("name"),
                "status": "stored",
                "object_sha256": stored["sha256"],
                "raw_size": stored["raw_size"],
            })
        except (GitHubError, OSError) as error:
            status = "expired" if isinstance(error, GitHubError) and error.status in (404, 410) else "retry"
            self.store.set_log(run_id, attempt, job_id, None, status)
            self.store.event("job-logs", {
                "run_id": run_id,
                "attempt": attempt,
                "job_id": job_id,
                "job_name": job.get("name"),
                "status": status,
                "http_status": error.status if isinstance(error, GitHubError) else None,
                "detail": str(error),
            })

    def download_artifact(self, run: dict[str, Any], attempt: int, artifact: dict[str, Any], fingerprint: str) -> None:
        run_id = int(run["id"])
        artifact_id = int(artifact["id"])
        name = artifact.get("name", "")
        api_digest = artifact.get("digest")
        digest = api_digest.removeprefix("sha256:").lower() if api_digest else None
        previous_blob, previous_status = self.store.get_artifact(run_id, attempt, artifact_id, fingerprint)

        decision = self.skip_artifact(name)
        if decision:
            self.store.set_artifact(run_id, attempt, artifact_id, fingerprint, None, decision)
            self.store.event("artifacts", {
                "run_id": run_id, "attempt": attempt, "artifact_id": artifact_id,
                "name": name, "api_digest": api_digest, "size_in_bytes": artifact.get("size_in_bytes"),
                "expires_at": artifact.get("expires_at"), "expired": artifact.get("expired"),
                "selection": decision, "status": decision, "api": artifact,
            })
            return
        if artifact.get("expired"):
            self.store.set_artifact(run_id, attempt, artifact_id, fingerprint, None, "expired")
            status = "expired"
            blob = None
        elif digest and self.store.has_verified(digest):
            self.store.set_artifact(run_id, attempt, artifact_id, fingerprint, digest, "reused-digest")
            status = "reused-digest"
            blob = digest
        elif previous_blob and self.store.has_verified(previous_blob):
            self.store.set_artifact(run_id, attempt, artifact_id, fingerprint, previous_blob, "reused-occurrence")
            status = "reused-occurrence"
            blob = previous_blob
        else:
            try:
                body, media_type = self.api.download(
                    f"{API_ROOT}{self.repo_api}/actions/artifacts/{artifact_id}/zip"
                )
                stored = self.store.put(body, media_type, name=f"{name}.zip", expected_sha256=digest)
                blob = stored["sha256"]
                status = "stored"
                self.store.set_artifact(run_id, attempt, artifact_id, fingerprint, blob, status)
            except (GitHubError, OSError) as error:
                status = "expired" if isinstance(error, GitHubError) and error.status in (404, 410) else "retry"
                blob = None
                self.store.set_artifact(run_id, attempt, artifact_id, fingerprint, None, status)
                self.store.event("artifacts", {
                    "run_id": run_id, "attempt": attempt, "artifact_id": artifact_id,
                    "name": name, "api_digest": api_digest, "size_in_bytes": artifact.get("size_in_bytes"),
                    "selection": "download", "status": status,
                    "http_status": error.status if isinstance(error, GitHubError) else None,
                    "detail": str(error), "api": artifact,
                })
                return
            except ValueError as error:
                self.store.set_artifact(run_id, attempt, artifact_id, fingerprint, None, "digest-mismatch")
                self.store.event("artifacts", {
                    "run_id": run_id, "attempt": attempt, "artifact_id": artifact_id,
                    "name": name, "api_digest": api_digest, "selection": "download",
                    "status": "digest-mismatch", "detail": str(error), "api": artifact,
                })
                return

        self.store.event("artifacts", {
            "run_id": run_id, "attempt": attempt, "artifact_id": artifact_id,
            "name": name, "api_digest": api_digest, "blob_sha256": blob,
            "size_in_bytes": artifact.get("size_in_bytes"),
            "expires_at": artifact.get("expires_at"), "expired": artifact.get("expired"),
            "selection": "download", "status": status, "api": artifact,
        })

    def process_run(
        self,
        run: dict[str, Any],
        download_pool: concurrent.futures.ThreadPoolExecutor,
    ) -> None:
        run_id = int(run["id"])
        tasks: list[concurrent.futures.Future[Any]] = []
        attempts = max(1, int(run.get("run_attempt") or 1))
        for attempt in range(1, attempts + 1):
            attempt_data, _, attempt_sha = self.api.json(
                f"{self.repo_api}/actions/runs/{run_id}/attempts/{attempt}"
            )
            self.store.event("run-attempts", {
                "run_id": run_id, "attempt": attempt, "object_sha256": attempt_sha, "api": attempt_data,
            })
            jobs = self.list_all(
                f"{self.repo_api}/actions/runs/{run_id}/attempts/{attempt}/jobs",
                "jobs",
            )
            for job in jobs:
                self.store.event("jobs", {
                    "run_id": run_id, "attempt": attempt, "job_id": job.get("id"), "api": job,
                })
                if job.get("status") == "completed":
                    blob, status = self.store.get_log(run_id, attempt, int(job["id"]))
                    if status != "stored" or not self.store.has_verified(blob):
                        tasks.append(download_pool.submit(self.download_job_log, run, attempt, job))

        artifacts = self.list_all(f"{self.repo_api}/actions/runs/{run_id}/artifacts", "artifacts")
        for artifact in artifacts:
            fingerprint = self.artifact_fingerprint(artifact)
            self.store.event("artifact-observations", {
                "run_id": run_id, "attempt": attempts,
                "artifact_id": artifact.get("id"), "fingerprint": fingerprint,
                "api_digest": artifact.get("digest"), "api": artifact,
            })
            old_blob, old_status = self.store.get_artifact(run_id, attempts, int(artifact["id"]), fingerprint)
            if old_status in {"stored", "reused-digest", "reused-occurrence", "skipped-docker", "expired"}:
                if old_blob and self.store.has_verified(old_blob):
                    continue
                if old_status in {"skipped-docker", "expired"}:
                    continue
            tasks.append(download_pool.submit(self.download_artifact, run, attempts, artifact, fingerprint))

        for task in concurrent.futures.as_completed(tasks):
            task.result()
        self.store.save_run(run)

    def collect_actions(
        self,
        linked_pr_details: list[dict[str, Any]],
        hourly_reconcile: bool,
    ) -> int:
        runs = self.list_all(f"{self.repo_api}/actions/runs", "workflow_runs")
        linked_ids: set[int] = set()
        for detail in linked_pr_details:
            sha = (detail.get("head") or {}).get("sha")
            if not sha:
                continue
            related = self.list_all(
                f"{self.repo_api}/actions/runs?head_sha={urllib.parse.quote(sha)}",
                "workflow_runs",
            )
            linked_ids.update(int(item["id"]) for item in related)
        now = utc_now()
        cutoff_recent = now - dt.timedelta(hours=1)
        cutoff_reconcile = now - dt.timedelta(hours=24)
        candidates: list[dict[str, Any]] = []
        retry_ids = self.store.pending_run_ids()
        for run in runs:
            run_id = int(run["id"])
            previous = self.store.get_state(f"run:{run_id}:updated_at")
            created = parse_time(run.get("created_at"))
            active = run.get("status") != "completed"
            is_recent = created is not None and created >= cutoff_recent
            is_hourly = hourly_reconcile and created is not None and created >= cutoff_reconcile
            changed = previous != run.get("updated_at")
            if changed or active or is_recent or is_hourly or run_id in linked_ids or run_id in retry_ids:
                candidates.append(run)
        def run_priority(run: dict[str, Any]) -> tuple[int, int, int, float]:
            run_id = int(run["id"])
            previous = self.store.get_state(f"run:{run_id}:updated_at")
            created = parse_time(run.get("created_at"))
            return (
                0 if run_id in linked_ids else 1,
                0 if run.get("status") != "completed" else 1,
                0 if previous != run.get("updated_at") else 1,
                -(created.timestamp() if created else 0.0),
            )

        candidates.sort(key=run_priority)
        selected = candidates[: self.max_runs]
        failed = 0
        if selected:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.download_workers) as downloads:
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.api_workers) as api_pool:
                    futures = {api_pool.submit(self.process_run, run, downloads): run for run in selected}
                    for future in concurrent.futures.as_completed(futures):
                        run = futures[future]
                        try:
                            future.result()
                        except Exception as error:
                            failed += 1
                            self.store.event("collector", {
                                "kind": "run-capture-error",
                                "run_id": run.get("id"),
                                "detail": f"{type(error).__name__}: {error}",
                            })
                            continue
                        self.store.set_state(f"run:{run['id']}:updated_at", run.get("updated_at"))
        pending = max(0, len(candidates) - len(selected)) + failed
        self.store.event("collector", {
            "kind": "actions-scan",
            "runs_returned": len(runs),
            "runs_selected": len(selected),
            "runs_pending": pending,
            "hourly_reconcile": hourly_reconcile,
        })
        return pending

    def postprocess(self) -> None:
        manifest = self.store.manifest(self.repository)
        target = self.root / "manifests" / "latest.json.gz"
        temporary = target.with_suffix(".json.gz.tmp")
        with temporary.open("wb") as raw:
            with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, filename="") as zipped:
                zipped.write(canonical_json(manifest))
        os.replace(temporary, target)
        mirror = os.environ.get("CI_ARCHIVE_MIRROR_DESTINATION")
        if mirror:
            rclone = os.environ.get("CI_ARCHIVE_RCLONE_BIN", "rclone")
            log_path = self.logs_dir / "mirror-latest.log"
            with log_path.open("ab") as log:
                result = subprocess.run(
                    [rclone, "copy", str(self.root), mirror,
                     "--exclude", "/working-github-backup/**",
                     "--transfers", str(self.download_workers),
                     "--checkers", str(self.api_workers), "--log-level", "INFO"],
                    stdout=log, stderr=subprocess.STDOUT, check=False, timeout=1800,
                    env=os.environ.copy(),
                )
                if result.returncode == 0:
                    git_destination = os.environ.get(
                        "CI_ARCHIVE_MIRROR_GIT_DESTINATION", mirror.rstrip("/") + "/repository-git"
                    )
                    for head_file in self.github_backup_dir.rglob("HEAD"):
                        candidate = head_file.parent
                        if not (candidate / "objects").is_dir():
                            continue
                        probe = subprocess.run(
                            ["git", "-C", str(candidate), "rev-parse", "--is-bare-repository"],
                            capture_output=True, text=True, check=False,
                        )
                        if probe.returncode == 0 and probe.stdout.strip() == "true":
                            result = subprocess.run(
                                [rclone, "copy", str(candidate), git_destination,
                                 "--transfers", str(self.download_workers),
                                 "--checkers", str(self.api_workers), "--log-level", "INFO"],
                                stdout=log, stderr=subprocess.STDOUT, check=False, timeout=1800,
                                env=os.environ.copy(),
                            )
                            break
            self.store.event("collector", {
                "kind": "mirror",
                "destination": mirror,
                "git_destination": os.environ.get("CI_ARCHIVE_MIRROR_GIT_DESTINATION"),
                "exit_code": result.returncode,
            })
            if result.returncode != 0:
                raise RuntimeError(f"archive mirror failed; see {log_path}")

    def once(self, force_hourly: bool = False) -> dict[str, Any]:
        now = utc_now()
        last_pr_reconcile = parse_time(self.store.get_state("last_pr_reconcile"))
        last_actions_reconcile = parse_time(self.store.get_state("last_actions_reconcile"))
        pr_hourly = force_hourly or last_pr_reconcile is None or (now - last_pr_reconcile) >= dt.timedelta(hours=1)
        actions_hourly = force_hourly or last_actions_reconcile is None or (now - last_actions_reconcile) >= dt.timedelta(hours=1)
        _pr_details, action_links, pr_refresh = self.capture_pr_data(force=pr_hourly)
        if pr_hourly:
            self.store.set_state("last_pr_reconcile", iso_now())
        pending = self.collect_actions(action_links, hourly_reconcile=actions_hourly)
        if actions_hourly and pending == 0:
            self.store.set_state("last_actions_reconcile", iso_now())
        self.store.set_state("last_successful_cycle", iso_now())
        self.postprocess()
        return {
            "repository": self.repository,
            "pr_refresh": pr_refresh,
            "hourly_reconcile": actions_hourly,
            "runs_pending": pending,
            "manifest": self.store.manifest(self.repository),
        }

    def close(self) -> None:
        self.store.close()


def config_path(value: str | None, env: str, label: str) -> Path:
    path = value or os.environ.get(env)
    if not path:
        raise SystemExit(f"{label} is required via {env} or command-line option")
    return Path(path).expanduser()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default=os.environ.get("CI_ARCHIVE_REPOSITORY", DEFAULT_REPOSITORY))
    parser.add_argument("--root", help="archive data root; otherwise CI_ARCHIVE_ROOT")
    parser.add_argument("--token-file", help="GitHub token file; otherwise CI_ARCHIVE_GITHUB_TOKEN_FILE")
    parser.add_argument("--uvx", default=os.environ.get("CI_ARCHIVE_UVX", shutil.which("uvx") or "uvx"))
    parser.add_argument("--max-runs", type=int, default=int(os.environ.get("CI_ARCHIVE_MAX_RUNS_PER_CYCLE", DEFAULT_MAX_RUNS)))
    parser.add_argument("--api-workers", type=int, default=int(os.environ.get("CI_ARCHIVE_API_WORKERS", DEFAULT_API_WORKERS)))
    parser.add_argument("--download-workers", type=int, default=int(os.environ.get("CI_ARCHIVE_DOWNLOAD_WORKERS", DEFAULT_DOWNLOAD_WORKERS)))
    parser.add_argument("--max-qps", type=float, default=float(os.environ.get("CI_ARCHIVE_MAX_API_QPS", DEFAULT_MAX_QPS)))
    parser.add_argument("--min-free-bytes", type=int, default=int(os.environ.get("CI_ARCHIVE_MIN_FREE_BYTES", 4 * 1024 * 1024 * 1024)))
    parser.add_argument("--hourly-reconcile", action="store_true", help="force the overlapping 24-hour repair scan")
    args = parser.parse_args(argv)

    root = config_path(args.root, "CI_ARCHIVE_ROOT", "archive root")
    token_file = config_path(args.token_file, "CI_ARCHIVE_GITHUB_TOKEN_FILE", "GitHub token file")
    if args.max_runs < 1 or args.api_workers < 1 or args.download_workers < 1:
        parser.error("worker and run limits must be positive")
    collector = Collector(
        repository=args.repository,
        root=root,
        token_file=token_file,
        uvx=args.uvx,
        max_runs=args.max_runs,
        api_workers=args.api_workers,
        download_workers=args.download_workers,
        qps=args.max_qps,
        min_free_bytes=args.min_free_bytes,
    )
    try:
        result = collector.once(force_hourly=args.hourly_reconcile)
        print(json.dumps(result, sort_keys=True))
    finally:
        collector.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

