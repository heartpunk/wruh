"""Shared selection and inventory for the Python and Lean extractors."""
from __future__ import annotations

import hashlib
import json

from extractor.instruction_inventory import Interval, inventory_project
from extractor.loaded_image import load_object_set
from extractor.fresh import linear_site_records


def prepare(args):
    exclusions = []
    if args.data_intervals is not None:
        raw = json.loads(args.data_intervals.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("data intervals must be an array")
        for item in raw:
            if not isinstance(item, dict) or set(item) != {"start", "end"}:
                raise ValueError("data intervals require start and end")
            if type(item["start"]) is not int or type(item["end"]) is not int:
                raise ValueError("data interval addresses must be integers")
            exclusions.append(Interval(item["start"], item["end"]))
    project = load_object_set(args.artifact, args.objects)
    inv = inventory_project(project, exclusions)
    records = linear_site_records(project, inv, chunk_size=args.chunk_size, seed=args.seed)
    report = {
        "decoded": len(inv.decoded),
        "data_intervals": [{"start": item.start, "end": item.end} for item in exclusions],
        "unresolved": [{"start": item.start, "end": item.end} for item in inv.unresolved],
        "unexamined": [{"start": item.start, "end": item.end} for item in inv.unexamined],
    }
    return project, records, report, hashlib.sha256(args.artifact.read_bytes()).hexdigest()
