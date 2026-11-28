"""Prepare and validate object-relative extraction selectors for the stock ELF."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

SELECTOR_SCHEMA = "wruh-fresh-selector-v1"


def read_selector(path, image, digest):
    from extractor.artifact import DecodedInstructionEvidence, Occurrence

    selector = json.loads(path.read_text())
    if set(selector) != {"schema", "image_sha256", "start", "end", "occurrences"}:
        raise ValueError("invalid selector fields")
    if selector["schema"] != SELECTOR_SCHEMA or selector["image_sha256"] != digest:
        raise ValueError("invalid selector schema or image digest")
    start, end = selector["start"], selector["end"]
    if type(start) is not int or type(end) is not int or not 0 <= start < end:
        raise ValueError("invalid selector window")
    if not isinstance(selector["occurrences"], list) or not selector["occurrences"]:
        raise ValueError("selector must contain occurrences")
    obj, = image.loaded_image["objects"]
    if obj["sha256"] != digest:
        raise ValueError("selector requires the single pinned object")
    segments = [
        (segment["address"], bytes.fromhex(segment["bytes"]))
        for segment in obj["segments"] if segment["executable"]
    ]
    records = []
    previous_end = 0
    for raw in selector["occurrences"]:
        occurrence = Occurrence.from_data(raw)
        origin = occurrence.origin
        if (not isinstance(origin, DecodedInstructionEvidence)
                or origin.image_sha256 != digest
                or origin.mapped_base != obj["mapped_base"]
                or origin.architecture != "AMD64" or origin.decode_mode != "long64"
                or origin.object_offset is None or not start <= origin.object_offset < end
                or occurrence.id.value != origin.source or origin.source < previous_end):
            raise ValueError("invalid selector occurrence")
        code = bytes.fromhex(origin.instruction_bytes)
        if not 1 <= len(code) <= 15 or not any(
            address <= origin.source
            and data[origin.source - address:origin.source - address + len(code)] == code
            for address, data in segments
        ):
            raise ValueError("selector occurrence does not match executable bytes")
        records.append((origin.source, occurrence))
        previous_end = origin.source + len(code)
    return tuple(records)


def prepare_catalog(args):
    from extractor.linear_pipeline import prepare

    settings = json.loads(args.settings.read_text())
    window = settings["window_bytes"]
    if window <= 0:
        raise ValueError("window size must be positive")
    args.scope_bytes = settings["scope_bytes"]
    session, records, report, digest = prepare(args)
    if len(session.image.loaded_image["objects"]) != 1:
        raise ValueError("catalog requires a single object")
    jobs = defaultdict(list)
    for _, occurrence in sorted(records, key=lambda record: record[0]):
        start = occurrence.origin.object_offset // window * window
        jobs[start].append(occurrence.to_data())
    if not jobs:
        raise ValueError("extraction scope contains no decoded instructions")

    directory = args.catalog
    directory.mkdir()
    selectors = []
    for start, occurrences in sorted(jobs.items()):
        filename = f"window_{start:016x}.json"
        selectors.append(filename)
        payload = {
            "schema": SELECTOR_SCHEMA, "image_sha256": digest, "start": start,
            "end": start + window, "occurrences": occurrences,
        }
        (directory / filename).write_text(json.dumps(payload, sort_keys=True) + "\n")
    (directory / "jobs.bzl").write_text("SELECTORS = " + json.dumps(selectors, indent=4) + "\n")
    (directory / "metadata.json").write_text(json.dumps({
        "image_sha256": digest, "loaded_image": session.image.loaded_image, "inventory": report,
    }, sort_keys=True) + "\n")
    (directory / "lua.elf").write_bytes(args.artifact.read_bytes())
    (directory / "BUILD.bazel").write_text(
        'exports_files(glob(["*.json"]) + ["lua.elf", "jobs.bzl"], visibility = ["//visibility:public"])\n'
    )
    (directory / "MODULE.bazel").write_text('module(name = "wruh_lua_catalog")\n')


def main():
    from extractor.extraction_args import add_arguments
    from extractor.native_runtime import preload_libstdcxx

    parser = argparse.ArgumentParser()
    add_arguments(parser)
    parser.add_argument("--settings", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    args = parser.parse_args()
    if args.objects is not None or args.scope_bytes is not None:
        parser.error("catalog uses one object and the declared scope setting")
    preload_libstdcxx()
    prepare_catalog(args)


if __name__ == "__main__":
    main()
