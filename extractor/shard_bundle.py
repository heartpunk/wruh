"""Assemble fresh instruction shards after decoding their local AYXG DAGs."""

from __future__ import annotations

from ayxg.codec import dumps, loads

BUNDLE_SCHEMA = "wruh-fresh-bundle-v2"
SHARD_SCHEMA = "wruh-fresh-shard-v1"


def merge(metadata, shards):
    occurrences = {}
    edges = {}
    common = None
    for shard in shards:
        if shard["schema"] != SHARD_SCHEMA or shard["image_sha256"] != metadata["image_sha256"]:
            raise ValueError("shard image or schema differs from the catalog")
        extraction = shard["extraction"]
        header = {key: extraction[key] for key in ("schema", "declarations", "architecture")}
        if common is not None and common != header:
            raise ValueError("shard extraction headers differ")
        common = header
        local_ids = set()
        for occurrence in extraction["occurrences"]:
            identity = occurrence["static_occurrence_id"]
            if identity in occurrences:
                raise ValueError(f"duplicate occurrence: {identity}")
            occurrences[identity] = occurrence
            local_ids.add(identity)
        for edge in extraction["local_edges"]:
            identity = edge["edge_id"]
            key = (identity["static_occurrence_id"], identity["outcome_id"])
            if key[0] not in local_ids or key in edges:
                raise ValueError(f"orphan or duplicate local edge: {key}")
            edges[key] = edge
    if common is None:
        raise ValueError("no extraction shards")
    return {
        **metadata,
        "schema": BUNDLE_SCHEMA,
        "extraction": {
            **common,
            "occurrences": [occurrences[key] for key in sorted(occurrences)],
            "local_edges": [edges[key] for key in sorted(edges)],
        },
    }


def encode(payload):
    # The codec assigns root IDs in traversal order, before sorting JSON keys.
    def ordered(value):
        if isinstance(value, dict):
            if "op" in value and "sort" in value:
                return value  # Preserve sharing in TypedExpr.to_data() DAGs.
            return {key: ordered(value[key]) for key in sorted(value)}
        if isinstance(value, list):
            return [ordered(item) for item in value]
        return value

    return dumps(ordered(payload), indent=2, sort_keys=True) + "\n"


def main():
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("metadata", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("shards", type=Path, nargs="+")
    args = parser.parse_args()
    metadata = json.loads(args.metadata.read_text())
    shards = (loads(path.read_text()) for path in args.shards)
    args.output.write_text(encode(merge(metadata, shards)))


if __name__ == "__main__":
    main()
