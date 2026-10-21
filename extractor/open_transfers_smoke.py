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
    def edge(pc, index, target, x_after=None):
        value = target.value if target.kind == 'symbolic' else TypedExpr.bv_lit(64, target.value or 0)
        return LocalEdge(EdgeId(StaticOccurrenceId(index), OutcomeId(0)), pc,
            StepSummary(TypedExpr.equal(TypedExpr.var('rip', TermSort.bv(64)), TypedExpr.bv_lit(64,pc)),
                (Assignment('rip',value), Assignment('x',x_after if x_after is not None else TypedExpr.var('x',TermSort.bv(64)))), target, value))
    indirect = edge(100,0,Target('symbolic', TypedExpr.var('x',TermSort.bv(64))), TypedExpr.bv_lit(64,0))
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
    original_open=[path for path in open_paths if path.target.value==TypedExpr.var('x',TermSort.bv(64))]
    assert len(original_open)==1
    check(z3.Xor(expr_to_z3(original_open[0].guard,variables,ctx),z3.And(variables['rip']==100,variables['x']!=200,variables['x']!=100)))
    for target,resolution in [(None,CallResolution()),(300,CallResolution()),(300,CallResolution(plt_names=('puts',)))]:
        assert classify_call(encoded_target=target,resolution=resolution,selected_symbols=frozenset(),declared_primitives=frozenset(),open_transfers=True)[0] is CallKind.OPEN
        try: classify_call(encoded_target=target,resolution=resolution,selected_symbols=frozenset(),declared_primitives=frozenset())
        except InventoryError: pass
        else: raise AssertionError('strict provider admission changed')
    # No candidate: exact symbolic transfer must survive, not raise or havoc.
    isolated=compose_fresh_paths({'roots':{'caller':cfg['roots']['caller']}},functions[:1],'caller')
    assert any(path.target.kind=='symbolic' for path in isolated)
    # Tail transfer follows the callee without inventing a new return frame.
    tail_cfg={'roots':{'caller':root(100,'jmp'), 'callee':cfg['roots']['callee']}}
    tail_edge=edge(100,0,Target('address',200))
    tail_functions=(FreshFunction('caller',100,declarations,(),(tail_edge,)), functions[1])
    tail_paths=compose_fresh_paths(tail_cfg,tail_functions,'caller')
    assert len(tail_paths)==1 and tail_paths[0].target==Target('address',105)
    # An external direct call retains its exact poststate and target.
    outside_edge=edge(100,0,Target('address',300))
    outside_cfg={'roots':{'caller':root(100,'call',[{'address':100,'target':300,'kind':'open','name':'external'}])}}
    outside_paths=compose_fresh_paths(outside_cfg,(FreshFunction('caller',100,declarations,(),(outside_edge,)),),'caller')
    assert len(outside_paths)==1 and outside_paths[0].target==Target('address',300)
    assert outside_paths[0].update['rip']==TypedExpr.bv_lit(64,300)
    # Symbolic self-call is an admitted equality branch, not an open residual.
    self_call=edge(100,0,Target('symbolic',TypedExpr.var('x',TermSort.bv(64))),TypedExpr.bv_lit(64,0))
    self_halt=edge(100,1,Target('halt'))
    from dataclasses import replace
    xvar=TypedExpr.var('x',TermSort.bv(64)); zero=TypedExpr.bv_lit(64,0)
    self_call=replace(self_call,summary=replace(self_call.summary,guard=TypedExpr.conjoin(self_call.summary.guard,TypedExpr.not_equal(xvar,zero))))
    self_halt=replace(self_halt,summary=replace(self_halt.summary,guard=TypedExpr.conjoin(self_halt.summary.guard,TypedExpr.equal(xvar,zero))))
    self_cfg={'roots':{'caller':root(100,'call',[{'address':100,'target':None,'kind':'open','name':'indirect'}])}}
    self_paths=compose_fresh_paths(self_cfg,(FreshFunction('caller',100,declarations,(),(self_call,self_halt)),),'caller',max_steps=8)
    halt_guards=[expr_to_z3(path.guard,variables,ctx) for path in self_paths if path.target.kind=='halt']
    check(z3.Xor(z3.Or(*halt_guards),z3.And(variables['rip']==100,z3.Or(variables['x']==0,variables['x']==100))))
    check(z3.Xor(z3.Or(*(expr_to_z3(path.guard,variables,ctx) for path in self_paths)),variables['rip']==100))
    result = {'self_call':'admitted and terminates after state update','tail_transfer':'no invented return frame','direct_external':'exact target/poststate retained','partition':'complete and disjoint UNSAT checks','admission':'3 open / 3 strict rejects','no_candidate':'exact symbolic target preserved'}
    parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path); args=parser.parse_args()
    if args.output: args.output.write_text(json.dumps(result,sort_keys=True)+'\n')
    print(json.dumps(result))

if __name__=='__main__': main()
