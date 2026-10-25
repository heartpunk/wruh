import datetime as dt
import gzip
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.ci_archive import ArchiveStore, Collector, digest_bytes


class ArchiveStoreTests(unittest.TestCase):
    def test_json_payload_is_gzipped_and_deduplicated_by_raw_sha256(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = ArchiveStore(Path(temporary), min_free_bytes=0)
            payload = b'{"hello":"archive"}\n'
            first = store.put(payload, "application/json", name="one.json")
            second = store.put(payload, "application/json", name="two.json")
            self.assertEqual(first["sha256"], digest_bytes(payload))
            self.assertEqual(first["sha256"], second["sha256"])
            self.assertEqual(first["encoding"], "gzip")
            self.assertTrue(second["deduplicated"])
            stored = (Path(temporary) / first["path"]).read_bytes()
            self.assertEqual(gzip.decompress(stored), payload)
            self.assertTrue(store.has_verified(first["sha256"]))
            store.close()

    def test_digest_mismatch_is_rejected_before_an_object_is_registered(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = ArchiveStore(Path(temporary))
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                store.put(b"actual", "application/zip", expected_sha256="0" * 64)
            count = store.conn.execute("SELECT COUNT(*) FROM objects").fetchone()[0]
            self.assertEqual(count, 0)
            store.close()

    def test_occurrence_records_are_gzip_members(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = ArchiveStore(Path(temporary))
            store.event("artifacts", {"artifact_id": 7, "selection": "download"})
            path = Path(temporary) / "records" / "artifacts.jsonl.gz"
            self.assertIn(b'"artifact_id":7', gzip.decompress(path.read_bytes()))
            store.close()

    def test_artifact_occurrences_keep_attempt_identity_and_retry_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = ArchiveStore(Path(temporary))
            store.set_artifact(100, 1, 7, "fingerprint", "a" * 64, "stored")
            store.set_artifact(100, 2, 7, "fingerprint", "b" * 64, "retry")
            self.assertEqual(store.get_artifact(100, 1, 7, "fingerprint"), ("a" * 64, "stored"))
            self.assertEqual(store.get_artifact(100, 2, 7, "fingerprint"), ("b" * 64, "retry"))
            store.set_log(100, 2, 99, None, "retry")
            self.assertEqual(store.pending_run_ids(), {100})
            store.close()

    def test_census_jsonld_is_indexed_without_rewriting_original_archive(self):
        graph = [
            {"@id": "census", "@type": "bfe:ExtractionCensus", "bfe:censusUsesInventory": {"@id": "inventory"}},
            {"@id": "binary", "@type": "bfe:BinaryObject", "bfe:contentDigest": "sha256:" + "a" * 64},
            {"@id": "census/candidate/fn_0000000000000001", "@type": "bfe:FunctionCandidate", "bfe:candidateInObject": {"@id": "binary"}},
        ]
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, "w") as archive:
            archive.writestr("census.jsonld", json.dumps({"@graph": graph}))
        original = payload.getvalue()
        with tempfile.TemporaryDirectory() as temporary:
            store = ArchiveStore(Path(temporary), min_free_bytes=0)
            stored = store.put(original, "application/zip", name="binary-census.zip")
            store.set_artifact(1, 1, 1, "fixture", stored["sha256"], "stored")
            self.assertEqual(store.reindex_existing_census_archives(), 3)
            self.assertEqual(store.reindex_existing_census_archives(), 0)
            row = store.conn.execute(
                "SELECT binary_sha256, inventory_digest, inventory_id, candidate_id, evidence_state FROM census_entities WHERE entity_type='bfe:FunctionCandidate'"
            ).fetchone()
            self.assertEqual(row, ("a" * 64, None, "inventory", "fn_0000000000000001", "unknown"))
            self.assertEqual((Path(temporary) / stored["path"]).read_bytes(), original)
            store.close()

    def test_unreadable_retained_archive_is_recorded_as_unknown(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = ArchiveStore(Path(temporary), min_free_bytes=0)
            stored = store.put(b"not a zip archive", "application/zip", name="census.zip")
            store.set_artifact(1, 1, 2, "broken", stored["sha256"], "stored")
            self.assertEqual(store.reindex_existing_census_archives(), 0)
            row = store.conn.execute(
                "SELECT entity_type, evidence_state FROM census_entities WHERE report_sha256=?",
                (stored["sha256"],),
            ).fetchone()
            self.assertEqual(row, ("wruh:EvidenceGap", "unknown"))
            store.close()

    def test_docker_image_artifact_is_skipped_but_census_bundle_is_kept(self):
        self.assertEqual(Collector.skip_artifact("wruh-dev-linux-amd64"), "skipped-docker")
        self.assertEqual(Collector.skip_artifact("docker-image-layer"), "skipped-docker")
        self.assertIsNone(Collector.skip_artifact("binary-census-cpython"))
        self.assertIsNone(Collector.skip_artifact("function-artifacts.tar.gz"))


class CollectorSchedulingTests(unittest.TestCase):
    @staticmethod
    def make_collector(store, runs, max_runs, processed):
        collector = Collector.__new__(Collector)
        collector.store = store
        collector.repo_api = "/repos/heartpunk/wruh"
        collector.max_runs = max_runs
        collector.api_workers = 1
        collector.download_workers = 1
        collector.list_all = lambda _path, _key=None: runs

        def process_run(run, _download_pool):
            processed.append(int(run["id"]))
            store.save_run(run)

        collector.process_run = process_run
        return collector

    @staticmethod
    def run_record(run_id, status="completed", created_at=None, updated_at=None):
        now = dt.datetime.now(dt.timezone.utc)
        return {
            "id": run_id,
            "status": status,
            "created_at": (created_at or now - dt.timedelta(hours=2)).isoformat().replace("+00:00", "Z"),
            "updated_at": (updated_at or now - dt.timedelta(hours=2)).isoformat().replace("+00:00", "Z"),
            "completed_at": None if status != "completed" else now.isoformat().replace("+00:00", "Z"),
            "run_attempt": 1,
        }

    def test_hourly_reconcile_queue_advances_across_capped_polls(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = ArchiveStore(Path(temporary))
            now = dt.datetime.now(dt.timezone.utc)
            runs = [
                self.run_record(i, created_at=now - dt.timedelta(hours=2), updated_at=now - dt.timedelta(hours=2))
                for i in range(1, 6)
            ]
            for run in runs:
                store.save_run(run)
                store.set_state(f"run:{run['id']}:updated_at", run["updated_at"])
            processed = []
            collector = self.make_collector(store, runs, max_runs=2, processed=processed)

            first_pending = collector.collect_actions([], hourly_reconcile=True)
            self.assertEqual(first_pending, 3)
            self.assertEqual(len(processed), 2)
            self.assertEqual(len(store.actions_reconcile_run_ids()), 3)

            second_pending = collector.collect_actions([], hourly_reconcile=False)
            self.assertEqual(second_pending, 1)
            self.assertEqual(len(processed), 4)
            self.assertEqual(len(store.actions_reconcile_run_ids()), 1)

            final_pending = collector.collect_actions([], hourly_reconcile=False)
            self.assertEqual(final_pending, 0)
            self.assertEqual(set(processed), {1, 2, 3, 4, 5})
            self.assertEqual(store.actions_reconcile_run_ids(), set())
            store.close()

    def test_stable_active_run_waits_for_change_or_hourly_reconcile(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = ArchiveStore(Path(temporary))
            now = dt.datetime.now(dt.timezone.utc)
            run = self.run_record(
                99,
                status="in_progress",
                created_at=now - dt.timedelta(minutes=30),
                updated_at=now - dt.timedelta(minutes=1),
            )
            store.save_run(run)
            store.set_state(f"run:{run['id']}:updated_at", run["updated_at"])
            processed = []
            collector = self.make_collector(store, [run], max_runs=25, processed=processed)

            self.assertEqual(collector.collect_actions([], hourly_reconcile=False), 0)
            self.assertEqual(processed, [])

            run["updated_at"] = now.isoformat().replace("+00:00", "Z")
            self.assertEqual(collector.collect_actions([], hourly_reconcile=False), 0)
            self.assertEqual(processed, [99])
            store.close()


if __name__ == "__main__":
    unittest.main()
