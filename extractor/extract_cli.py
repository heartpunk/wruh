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
    args = parser.parse_args()
    from extractor.native_runtime import preload_libstdcxx
    preload_libstdcxx()
    from ayxg.codec import dumps

    from extractor.fresh import extract_linear
    from extractor.linear_pipeline import prepare
    from extractor.loaded_image import loaded_image_data
    project, records, inventory, image_sha256 = prepare(args)
    result = {
        "schema": "wruh-fresh-bundle-v2", "image_sha256": image_sha256,
        "inventory": inventory, "extraction": extract_linear(project, records).to_data(),
        "loaded_image": loaded_image_data(project),
    }
    args.output.write_text(dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
