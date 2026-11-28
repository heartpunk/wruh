"""Compare extracted relations on shared instruction sites."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from extractor.native_runtime import preload_libstdcxx

preload_libstdcxx()
import z3
from ayxg.codec import loads
from ayxg.expr import Declaration, TypedExpr
from ayxg.z3 import declaration_variables, expr_to_z3

from extractor.parity_sites import attach_mapping_identity, combine_models, match_sites


def read_bundle(path: Path):
    raw = path.read_text(encoding='utf-8')
    data = json.loads(raw)
    if data.get('schema') == 'ayxg-artifact-dag-v1':
        data = loads(raw)
    data = attach_mapping_identity(data)
    return data, combine_models([data['extraction']] if 'extraction' in data else data['functions'])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    old_bundle, old = read_bundle(args.baseline)
    new_bundle, new = read_bundle(args.candidate)
    if old_bundle['image_sha256'] != new_bundle['image_sha256']:
        raise ValueError('input image digests differ')
    if old['declarations'] != new['declarations']:
        raise ValueError('state declarations differ')
    matched = match_sites(old, new)
    ctx = z3.Context()
    variables = declaration_variables(tuple(Declaration.from_data(item) for item in old['declarations']), ctx)

    def convert(value):
        return expr_to_z3(value if isinstance(value, TypedExpr) else TypedExpr.from_data(value), variables, ctx)

    checks = []
    for key, before, after in matched['shared_edges']:
        if before['source'] != after['source']:
            raise ValueError('transition comparison requires identical mappings; address normalization is not implemented')
        if before.get('jumpkind') != after.get('jumpkind') or before.get('fault_kind') != after.get('fault_kind'):
            raise ValueError(f'outcome metadata differs at {key!r}')
        left, right = before['summary'], after['summary']
        lg, rg = convert(left['guard']), convert(right['guard'])
        lu = {item['name']: convert(item['value']) for item in left['simultaneous_update']}
        ru = {item['name']: convert(item['value']) for item in right['simultaneous_update']}
        if lu.keys() != ru.keys() or lu.keys() != variables.keys():
            raise ValueError(f'update declarations differ at {key!r}')
        if left['target']['kind'] != right['target']['kind']:
            raise ValueError(f'target kinds differ at {key!r}')
        differences = [lu[name] != ru[name] for name in lu]
        differences.append(convert(left['mirrored_pc']) != convert(right['mirrored_pc']))
        if left['target']['kind'] == 'symbolic':
            differences.append(convert(left['target']['value']) != convert(right['target']['value']))
        elif left['target'] != right['target']:
            raise ValueError(f'target values differ at {key!r}')
        for kind, proposition in [('guard', lg != rg), ('state_and_target', z3.And(z3.Or(lg, rg), z3.Or(*differences)))]:
            solver = z3.Solver(ctx=ctx)
            solver.set(timeout=10000)
            solver.add(proposition)
            started = time.monotonic()
            result = solver.check()
            record = {'site': key[0], 'outcome': key[1], 'kind': kind,
                      'result': str(result), 'seconds': time.monotonic() - started}
            if result == z3.sat:
                record['counterexample'] = str(solver.model())
            elif result == z3.unknown:
                record['reason'] = solver.reason_unknown()
            checks.append(record)
    parity = bool(checks) and not matched['only_baseline_edges'] and not matched['only_candidate_edges'] and all(item['result'] == 'unsat' for item in checks)
    report = {'inventory_differences': {'only_baseline': matched['only_baseline_sites'], 'only_candidate': matched['only_candidate_sites']},
              'edge_differences_on_shared_sites': {'only_baseline': matched['only_baseline_edges'], 'only_candidate': matched['only_candidate_edges']},
              'checks': checks, 'shared_edge_parity': parity}
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    return 0 if parity else 1


if __name__ == '__main__':
    raise SystemExit(main())
