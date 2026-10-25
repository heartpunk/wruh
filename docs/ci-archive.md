# Wruh CI archive first wave

This prototype captures one repository so the archive can be exercised against live data before a larger control-plane design is chosen.

## Capture loop

Run `python3 tools/ci_archive.py` once every five minutes using an external timer. The first pass runs `github-backup` for the Wruh repository and all API-visible PRs. On later polls, the CLI runs incrementally when PR metadata changes; an hourly pass also refreshes PR data and reconciles Actions data from the preceding 24 hours. New or updated runs, runs linked to changed PR heads, and retryable captures take priority. Unchanged active runs do not consume every five-minute poll.

The collector uses a bounded API request rate, a bounded metadata worker pool, and a bounded download worker pool. Independent PR, job-log, and artifact downloads can proceed concurrently. It uses polling because this first wave has no webhook receiver; the timer configuration belongs to the deployment.

The CLI command is invoked as `uvx --from github-backup github-backup`. It captures the bare repository and PR details, commits, reviews, review comments, and conversation comments. A separate standard-library Python collector uses the GitHub Actions REST API for runs, attempts, jobs, terminal job logs, and artifact ZIPs.

## Archive format and repair evidence

- `objects/sha256/<prefix>/<sha256>` is a content-addressed store keyed by the raw payload SHA-256. JSON, text, and logs are gzip-compressed; ZIP artifacts remain unchanged. The GitHub artifact digest is checked against the downloaded bytes before the object is accepted.
- `records/*.jsonl.gz` contains append-only observations. Each artifact observation includes the run and attempt association, full API metadata, API digest, expiry, selection decision, and reused or stored object reference. Repeated occurrences retain their own metadata even when they reuse a blob.
- `ledger.sqlite3` tracks run cursors, object verification, artifact occurrences, and job-log retry state. `manifests/latest.json.gz` is regenerated after each capture batch.
The Actions backstop stores its run IDs in a persistent SQLite queue and drains the queue across capped five-minute polls. It advances the hourly watermark when a sweep is queued, preventing a nonempty queue from forcing the same 24-hour rescan on every poll. Newly discovered or updated runs and retryable items remain higher priority than repair work.
- The CLI's mutable working directory stays separate from the compressed archive tree. The compressed PR snapshots are imported into CAS after each CLI run. The bare Git clone is mirrored separately.
- Docker image payloads, including `wruh-dev-linux-amd64`, are skipped while their metadata is recorded. Census artifacts remain intact, including the JSON-LD files and `function-artifacts.tar.gz`.
- GitHub's reported digest is checked against the verified CAS before any artifact payload request. Logs and artifacts that are not available yet remain retryable; expired objects and Docker skips are explicit records.
- A configurable free-space floor prevents the local archive from consuming the last space on its filesystem. For the seven-day trial, watch `manifests/latest.json.gz` and both copies' available space.

The post-download pass imports the latest CLI JSON, deduplicates payloads by raw digest, writes the manifest, then copies the archive to the configured mirror. It runs only after the related Actions downloads finish, so each completed batch is ready for a later CI consumer. There is no Oxigraph import or artifact unpacking in this phase.

## Deployment contract

Keep all deployment-specific values outside this repository. Configure the following in the service environment and its external secret/configuration store:

- `CI_ARCHIVE_ROOT`: archive data root.
- `CI_ARCHIVE_GITHUB_TOKEN_FILE`: path to a read-only GitHub token file. The same token is passed to `github-backup` by a `file://` reference, so it never appears in process arguments.
- `CI_ARCHIVE_GITHUB_BACKUP_DIR`: mutable working directory used by the CLI; do not point it at the archive root.
- `CI_ARCHIVE_UVX`: path to `uvx`.
- `CI_ARCHIVE_MIRROR_DESTINATION`: configured `rclone` destination for compressed metadata, objects, ledger, and manifest.
- `CI_ARCHIVE_MIRROR_GIT_DESTINATION`: configured `rclone` destination for the bare repository.
- `CI_ARCHIVE_RCLONE_BIN`: `rclone` executable path.
- Optional limits: `CI_ARCHIVE_MAX_API_QPS`, `CI_ARCHIVE_API_WORKERS`, `CI_ARCHIVE_DOWNLOAD_WORKERS`, `CI_ARCHIVE_MAX_RUNS_PER_CYCLE`, and `CI_ARCHIVE_MIN_FREE_BYTES`.

Install one service invocation and a five-minute timer outside the repository. The program performs one capture batch and exits; a failed invocation leaves local data intact and the next timer retries unresolved artifacts and logs. Point the mirror at the configured durable storage destination. Do not configure retention cleanup during the evidence-gathering week.

The first-pass archive remains a raw evidence store. Review the seven-day volume, duplicate rate, compression ratio, API behavior, and mirror lag before choosing a generic service split or adding webhooks.

## Wruh ontology and advisory PR selection

`docs/ontology/wruh.ttl` defines the compact local vocabulary. Run outcomes (`passed`, `failed`, `incomplete`, `not run`) are separate from diagnoses; missing artifacts are unknown. `docs/ontology/pr-hypothesis-example.ttl` shows the limited hypothesis syntax. The fixed selector in `extractor/ontology_selector.py` accepts typed failure-kind IRIs only and emits a manifest bound to the digest of the canonical current inventory. Its mode is `all` or `explicit`; explicit mode lists sorted candidate IDs and the seeded complement sample. The manifest digest is computed externally over canonical manifest bytes. It has no arbitrary SPARQL or PR-authored query language.

The selector is advisory and does not schedule shards. Its trusted archive adapter input is versioned JSON with `selectionHistoryVersion: 1`, the exact `binarySha256`, `evidenceCoverage: "complete"`, and per-candidate records containing `candidateId`, typed `failureKind`, `evidenceState`, and `evidenceReference`. Current BFE archives contain function candidates, binary SHA-256, and object address space, but failure observations are raw stage/code strings; they lack typed `FailureKind` diagnoses and established evidence coverage. The current archive index therefore cannot emit that adapter format and the CLI returns `mode=all` for those records. It never joins on generic `targetId` or a run-scoped candidate IRI alone. When PR census input lacks trusted hypothesis/history metadata, the current complete six-binary PR census remains unchanged. The PR cannot prune matches or the complement sample. A later sharder must consume the manifest and frozen candidate costs without reinterpreting diagnoses or resampling. Full census coverage remains required on merges. Issue #55 tracks a later RO-Crate evidence-bundle investigation; this change does not implement RO-Crate.

