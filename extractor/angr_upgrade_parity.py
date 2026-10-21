"""Compare fixed old/new extracted edge relations; no candidate execution."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from extractor.native_runtime import preload_libstdcxx

preload_libstdcxx()
import z3
from ayxg.expr import Declaration, TypedExpr
from ayxg.z3 import declaration_variables, expr_to_z3


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--state-extension', action='store_true', help='compare only baseline state projection')
    args = parser.parse_args()
    report = []
    for path in sorted(args.candidate.glob('corpus_native_model_*.json')):
        if 'runtime-trace' in path.name:
            continue
        before = json.loads((args.baseline / path.name).read_text())
        after = json.loads(path.read_text())
        b, c = before['fresh_model'], after['fresh_model']
        assert before['elf_sha256'] == after['elf_sha256']
        assert before['cfg'] == after['cfg']
        if args.state_extension:
            candidate_declarations = {d['name']:d for d in c['declarations']}
            assert all(candidate_declarations[d['name']] == d for d in b['declarations'])
        else:
            assert b['declarations'] == c['declarations']
        assert b['occurrences'] == c['occurrences']
        assert len(b['local_edges']) == len(c['local_edges'])
        ctx = z3.Context()
        variables = declaration_variables(tuple(Declaration.from_data(x) for x in c['declarations']), ctx)
        def convert(value, variables=variables, ctx=ctx):
            return expr_to_z3(TypedExpr.from_data(value), variables, ctx)
        results = []
        for old, new in zip(b['local_edges'], c['local_edges']):
            assert old['edge_id'] == new['edge_id'] and old['source'] == new['source']
            bs, cs = old['summary'], new['summary']
            bg, cg = convert(bs['guard']), convert(cs['guard'])
            bu = {u['name']: convert(u['value']) for u in bs['simultaneous_update']}
            cu = {u['name']: convert(u['value']) for u in cs['simultaneous_update']}
            assert cu.keys() == variables.keys()
            assert set(bu) <= set(cu)
            if not args.state_extension:
                assert bu.keys() == cu.keys()
            assert bs['target']['kind'] == cs['target']['kind']
            differences = [bu[n] != cu[n] for n in bu]
            differences.append(convert(bs['mirrored_pc']) != convert(cs['mirrored_pc']))
            if bs['target']['kind'] == 'symbolic':
                differences.append(convert(bs['target']['value']) != convert(cs['target']['value']))
            else:
                assert bs['target'] == cs['target']
            for kind, proposition in [('guard', bg != cg), ('state_and_target', z3.And(z3.Or(bg, cg), z3.Or(*differences)))]:
                solver = z3.Solver(ctx=ctx)
                solver.set(timeout=10000)
                solver.add(proposition)
                start = time.monotonic()
                disposition = solver.check()
                result = {'edge_id': old['edge_id'], 'kind': kind, 'result': str(disposition), 'seconds': time.monotonic() - start}
                if disposition == z3.sat:
                    result['counterexample'] = str(solver.model())
                elif disposition == z3.unknown:
                    result['reason'] = solver.reason_unknown()
                results.append(result)
        row = {'file': path.name, 'checks': results, 'all_unsat': all(x['result'] == 'unsat' for x in results)}
        report.append(row)
        args.output.write_text(json.dumps(report, indent=2) + '\n')
        print(path.name, len(results), 'UNSAT' if row['all_unsat'] else 'INCOMPLETE_OR_MISMATCH', flush=True)
    if not report:
        raise RuntimeError("no candidate corpus models found; comparison evidence is empty")
    return 0 if all(row['all_unsat'] for row in report) else 1

if __name__ == '__main__':
    raise SystemExit(main())
