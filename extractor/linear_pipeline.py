"""Shared selection and inventory for the Python and Lean extractors."""
from __future__ import annotations

import hashlib
import json

from extractor.backend import Session
from extractor.fresh import linear_site_records
from extractor.instruction_inventory import Interval


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
    digest = hashlib.sha256(args.artifact.read_bytes()).hexdigest()
    session = Session.load(args.artifact, args.objects, digest)
    inv = session.inventory(exclusions)
    records = linear_site_records(inv, chunk_size=args.chunk_size, seed=args.seed)
    scope_bytes = getattr(args, "scope_bytes", None)
    if scope_bytes is not None:
        if scope_bytes <= 0:
            raise ValueError("scope size must be positive")
        limits = {
            (obj["sha256"], obj["mapped_base"]): min(executable) + scope_bytes
            for obj in session.image.loaded_image["objects"]
            if (executable := [
                segment["address"] for segment in obj["segments"]
                if segment["executable"] and segment["size"]
            ])
        }
        records = tuple(
            (address, occurrence)
            for address, occurrence in records
            if address < limits[occurrence.origin.image_sha256, occurrence.origin.mapped_base]
        )
    report = {
        "decoded": len(inv.decoded),
        "data_intervals": [{"start": item.start, "end": item.end} for item in exclusions],
        "unresolved": [{"start": item.start, "end": item.end} for item in inv.unresolved],
        "unexamined": [{"start": item.start, "end": item.end} for item in inv.unexamined],
    }
    return session, records, report, digest
