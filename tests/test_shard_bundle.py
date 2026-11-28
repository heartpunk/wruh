import json
import unittest

from ayxg.codec import loads
from ayxg.expr import TypedExpr

from extractor.shard_bundle import SHARD_SCHEMA, encode, merge


class ShardBundleTest(unittest.TestCase):
    def test_merge_decodes_local_dags_before_assigning_global_refs(self):
        def shard(address, target):
            return {
                "schema": SHARD_SCHEMA,
                "image_sha256": "image",
                "extraction": {
                    "schema": "wruh-fresh-instructions-v1",
                    "declarations": [],
                    "architecture": {},
                    "occurrences": [{"static_occurrence_id": address}],
                    "local_edges": [{
                        "edge_id": {"static_occurrence_id": address, "outcome_id": 0},
                        "summary": {"mirrored_pc": TypedExpr.bv_lit(64, target)},
                    }],
                },
            }

        metadata = {
            "image_sha256": "image",
            "inventory": {"decoded": 4, "unresolved": [{"start": 1, "end": 2}]},
            "loaded_image": {"objects": [{"sha256": "image"}]},
        }
        documents = [encode(shard(10, 11)), encode(shard(20, 23))]
        for document in documents:
            edge, = json.loads(document)["payload"]["extraction"]["local_edges"]
            self.assertEqual(edge["summary"]["mirrored_pc"], {"$expr": 0})
        shards = [loads(document) for document in documents]
        output = encode(merge(metadata, shards))
        self.assertEqual(output, encode(merge(metadata, reversed(shards))))
        result = loads(output)
        for key, expected in metadata.items():
            self.assertEqual(result[key], expected)
        edges = result["extraction"]["local_edges"]
        self.assertEqual([edge["summary"]["mirrored_pc"] for edge in edges],
                         [TypedExpr.bv_lit(64, 11), TypedExpr.bv_lit(64, 23)])
        with self.assertRaisesRegex(ValueError, "duplicate occurrence"):
            merge(metadata, [shards[0], shards[0]])
