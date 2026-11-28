"""Export independent fresh instruction transitions for a loaded image."""
from __future__ import annotations

from extractor.runtime_trace import start_runtime_trace

start_runtime_trace()

import argparse
from pathlib import Path

from extractor.extraction_args import add_arguments


def main() -> int:
    parser = argparse.ArgumentParser()
    # Delay importing the extraction stack so --help works without its runtime.
    add_arguments(parser)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--selector", type=Path, help="extract a validated stock ELF shard")
    args = parser.parse_args()
    if args.selector is not None and any(
        item is not None for item in (args.objects, args.data_intervals, args.scope_bytes)
    ):
        parser.error("--selector supplies the extraction scope for a single object")
    from extractor.native_runtime import preload_libstdcxx
    preload_libstdcxx()

    from extractor.fresh import extract_linear
    from extractor.linear_pipeline import prepare
    from extractor.shard_bundle import BUNDLE_SCHEMA, SHARD_SCHEMA, encode

    if args.selector is not None:
        import hashlib

        from extractor.backend import Session
        from extractor.shard_selector import read_selector

        digest = hashlib.sha256(args.artifact.read_bytes()).hexdigest()
        session = Session.load(args.artifact, digest=digest)
        records = read_selector(args.selector, session.image, digest)
        args.output.write_text(encode({
            "schema": SHARD_SCHEMA, "image_sha256": digest,
            "extraction": extract_linear(session, records).to_data(),
        }))
        return 0

    session, records, inventory, image_sha256 = prepare(args)
    result = {
        "schema": BUNDLE_SCHEMA, "image_sha256": image_sha256,
        "loaded_image": session.image.loaded_image,
        "inventory": inventory, "extraction": extract_linear(session, records).to_data(),
    }
    args.output.write_text(encode(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
