"""Attempt existing extraction for every exact catalogue encoding.

Each failure is reported with the iform and bytes; no failed form is skipped or
counted as a model. This is extraction coverage, not a native correctness test.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


def attempt(item: tuple[dict, str]) -> tuple[str, str, str, str]:
    row, xed = item
    form = row.get('iform', '<missing>')
    encoded = row.get('bytes', '<missing>')
    try:
        from extractor.catalogue_models import prepare_model
        from extractor.iform_candidates import xed_iform_decoder
        model = prepare_model(row, xed_iform_decoder(xed))
        return form, encoded, 'MODEL', f'{len(model.relation.outcomes)} outcomes'
    except Exception as exc:  # noqa: BLE001 - report each failed sweep row
        return form, encoded, 'INCOMPLETE', f'{type(exc).__name__}: {exc}'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('catalogue', type=Path)
    parser.add_argument('xed')
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--start', type=int, default=0, help='zero-based row to resume')
    args = parser.parse_args()
    if not 1 <= args.workers <= 4:
        parser.error('workers must be between 1 and 4')
    with args.catalogue.open() as stream:
        rows = [json.loads(line) for line in stream]
    if not rows or not 0 <= args.start < len(rows):
        parser.error('catalogue is empty or start is outside it')
    selected = rows[args.start:]
    counts = Counter()
    batch_size = 32 * args.workers
    for start in range(0, len(selected), batch_size):
        batch = selected[start:start + batch_size]
        # Closing each bounded pool avoids indefinitely retaining extracted models
        # and avoids the executor's max_tasks_per_child recycling deadlock.
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            for form, encoded, status, detail in pool.map(attempt, ((row, args.xed) for row in batch)):
                counts[status] += 1
                print(f'{status} {form} {encoded} {detail}', flush=True)
    print(f'SUMMARY start={args.start} rows={len(selected)} forms={len({r["iform"] for r in selected})} '
          f'models={counts["MODEL"]} incomplete={counts["INCOMPLETE"]}', flush=True)
    if counts['INCOMPLETE']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
