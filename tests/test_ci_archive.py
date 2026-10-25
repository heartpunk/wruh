import gzip
import tempfile
import unittest
from pathlib import Path

from tools.ci_archive import ArchiveStore, Collector, digest_bytes


class ArchiveStoreTests(unittest.TestCase):
    def test_json_payload_is_gzipped_and_deduplicated_by_raw_sha256(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = ArchiveStore(Path(temporary))
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

    def test_docker_image_artifact_is_skipped_but_census_bundle_is_kept(self):
        self.assertEqual(Collector.skip_artifact("wruh-dev-linux-amd64"), "skipped-docker")
        self.assertEqual(Collector.skip_artifact("docker-image-layer"), "skipped-docker")
        self.assertIsNone(Collector.skip_artifact("binary-census-cpython"))
        self.assertIsNone(Collector.skip_artifact("function-artifacts.tar.gz"))


if __name__ == "__main__":
    unittest.main()
