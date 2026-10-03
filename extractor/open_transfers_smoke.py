"""Exact target partition and admission controls (no candidate native execution)."""
from extractor.runtime_trace import start_runtime_trace
start_runtime_trace()
from pathlib import Path
import argparse
from extractor.native_runtime import preload_libstdcxx
preload_libstdcxx()
import json
import z3
from ayxg.expr import Declaration, TermSort, TypedExpr
from ayxg.z3 import declaration_variables, expr_to_z3
from extractor.artifact import Assignment, LocalEdge, StepSummary, EdgeId, StaticOccurrenceId, OutcomeId, Target
from extractor.fresh import FreshFunction
from extractor.fresh_composition import compose_fresh_paths
from extractor.binary_inventory import classify_call, CallResolution, CallKind, InventoryError


def main():
    declarations = (Declaration('rip', TermSort.bv(64)), Declaration('x', TermSort.bv(64)))
    def edge(pc, index, target):
        value = target.value if target.kind == 'symbolic' else TypedExpr.bv_lit(64, target.value or 0)
        return LocalEdge(EdgeId(StaticOccurrenceId(index), OutcomeId(0)), pc,
            StepSummary(TypedExpr.equal(TypedExpr.var('rip', TermSort.bv(64)), TypedExpr.bv_lit(64,pc)),
                (Assignment('rip',value), Assignment('x',TypedExpr.var('x',TermSort.bv(64)))), target, value))
    indirect = edge(100,0,Target('symbolic', TypedExpr.var('x',TermSort.bv(64))))
    callee = edge(200,1,Target('address',105))
    finish = edge(105,2,Target('halt'))
    def root(pc, mnemonic, calls=()):
        return {'address':pc,'blocks':[{'successors':[], 'instructions':[{'address':pc,'mnemonic':mnemonic,'size':5}]}], 'calls':calls}
    cfg={'roots':{'caller':root(100,'call', [{'address':100,'target':None,'kind':'open','name':'indirect'}]),
        'callee':root(200,'ret')}}
    cfg['roots']['caller']['blocks'][0]['instructions'].append({'address':105,'mnemonic':'ret','size':1})
    functions=(FreshFunction('caller',100,declarations,(),(indirect,finish)), FreshFunction('callee',200,declarations,(),(callee,)))
    paths=compose_fresh_paths(cfg,functions,'caller',max_steps=8)
    ctx=z3.Context(); variables=declaration_variables(declarations,ctx)
    def check(condition):
        solver=z3.Solver(ctx=ctx); solver.add(condition); assert solver.check()==z3.unsat
    guards=[expr_to_z3(path.guard,variables,ctx) for path in paths]
    check(z3.Xor(z3.Or(*guards), variables['rip']==100))
    for i,a in enumerate(guards):
        for b in guards[i+1:]: check(z3.And(a,b))
    open_paths=[path for path in paths if path.target.kind=='symbolic']
    assert len(open_paths)==1 and open_paths[0].target.value==TypedExpr.var('x',TermSort.bv(64))
    check(z3.Xor(expr_to_z3(open_paths[0].guard,variables,ctx),z3.And(variables['rip']==100,variables['x']!=200)))
    for target,resolution in [(None,CallResolution()),(300,CallResolution()),(300,CallResolution(plt_names=('puts',)))]:
        assert classify_call(encoded_target=target,resolution=resolution,selected_symbols=frozenset(),declared_primitives=frozenset(),open_transfers=True)[0] is CallKind.OPEN
        try: classify_call(encoded_target=target,resolution=resolution,selected_symbols=frozenset(),declared_primitives=frozenset())
        except InventoryError: pass
        else: raise AssertionError('strict provider admission changed')
    # No candidate: exact symbolic transfer must survive, not raise or havoc.
    isolated=compose_fresh_paths({'roots':{'caller':cfg['roots']['caller']}},functions[:1],'caller')
    assert len(isolated)==1 and isolated[0].target.kind=='symbolic'
    result = {'partition':'complete and disjoint UNSAT checks','admission':'3 open / 3 strict rejects','no_candidate':'exact symbolic target preserved'}
    parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path); args=parser.parse_args()
    if args.output: args.output.write_text(json.dumps(result,sort_keys=True)+'\n')
    print(json.dumps(result))

if __name__=='__main__': main()
