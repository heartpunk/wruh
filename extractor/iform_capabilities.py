"""Inspect every catalogue seed against generator and XED capabilities.

This is a generator diagnostic, not a semantics or native-execution test.
Failures and unsupported operands are counted, never skipped.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from extractor.iform_candidates import (
    CandidateError,
    CandidateTemplate,
    inspect_operands,
    xed_iform_decoder,
)


def inspect_catalogue(path: Path, xed: str) -> dict:
    identify = xed_iform_decoder(xed)
    forms = set()
    failures = []
    unsupported = []
    counts = Counter()
    with path.open() as source:
        for line_number, line in enumerate(source, 1):
            counts['rows'] += 1
            try:
                row = json.loads(line)
                form = row['iform']
                forms.add(form)
                template = CandidateTemplate(form, row['iced_code'], bytes.fromhex(row['bytes']), row['bitness'])
                template.generate({}, identify)
                info = inspect_operands(template)
                if info['unsupported_operands']:
                    unsupported.append({'line': line_number, 'iform': form,
                                        'operands': info['unsupported_operands']})
                else:
                    counts['recognized_operand_rows'] += 1
            except (CandidateError, KeyError, TypeError, ValueError) as exc:
                failures.append({'line': line_number, 'error': str(exc)})
    if not counts['rows']:
        raise ValueError('catalogue is empty')
    return {'rows': counts['rows'], 'iforms': len(forms),
            'recognized_operand_rows': counts['recognized_operand_rows'],
            'unsupported_operand_rows': unsupported, 'failures': failures}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('catalogue', type=Path)
    parser.add_argument('xed')
    args = parser.parse_args()
    report = inspect_catalogue(args.catalogue, args.xed)
    print(json.dumps(report, sort_keys=True))
    if report['failures'] or report['unsupported_operand_rows']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
