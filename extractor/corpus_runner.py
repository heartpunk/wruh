"""Bounded concrete execution of extracted local edges using AYXG semantics."""
from __future__ import annotations
from ayxg.expr import Declaration
from ayxg.qfabv import (ArraySort, BoolSort, QFAbvArrayValue, QFAbvContext,
                       QFAbvExpr, QFAbvUpdate, QFAbvValuation, decode_sort)
from ayxg.eval import eval_expr, eval_update
from extractor.artifact import LocalEdge

STORAGE = 0x100000
STACK = 0x200008  # SysV function entry: rsp mod 16 = 8.
RETURN = 0x300000

class CorpusRunner:
    def __init__(self, model: dict):
        self.context = QFAbvContext(tuple(Declaration.from_data(d) for d in model['declarations']))
        self.entry = model['entry']
        self.edges = {}
        for raw in model['local_edges']:
            edge = LocalEdge.from_data(raw)
            guard = QFAbvExpr(self.context, BoolSort(), edge.summary.guard)
            bindings = {a.name:a.value for a in edge.summary.simultaneous_update}
            update = QFAbvUpdate(self.context,self.context,tuple(
                QFAbvExpr(self.context,decode_sort(d.sort),bindings[d.name])
                for d in self.context.declarations))
            self.edges.setdefault(edge.source,[]).append((edge,guard,update))

    def run(self, inputs: tuple[int,int,int,int,int], limit: int = 256) -> dict:
        if len(inputs)!=5 or any(type(v) is not int or not 0 <= v <= 0xffffffff for v in inputs):
            raise ValueError("input outside audited uint32 domain")
        case,a,b,x,initial = inputs
        if case>2 or a>7 or b>7:raise ValueError("case/offset outside audited domain")
        words = [initial ^ i for i in range(8)]
        memory = {}
        for i,word in enumerate(words):
            for j in range(4):memory[STORAGE+4*i+j]=(word>>(8*j))&255
        for j in range(8):memory[STACK+j]=(RETURN>>(8*j))&255
        values={d.name:0 for d in self.context.declarations}
        values.update(rip=self.entry,rsp=STACK)
        if case==0:values.update(rdi=STORAGE+4*a,rsi=STORAGE+4*b,rdx=x)
        elif case==1:values.update(rdi=STORAGE+a,rsi=x)
        elif case==2:values.update(rdi=x,rsi=initial)
        else:raise ValueError('case outside harness domain')
        values['mem']=QFAbvArrayValue(ArraySort(64,8),0,tuple(sorted((k,v) for k,v in memory.items() if v)))
        state=QFAbvValuation(self.context,tuple(values[d.name] for d in self.context.declarations))
        trace=[]
        for _ in range(limit):
            values=dict(zip((d.name for d in self.context.declarations),state.values))
            pc=values['rip']
            if pc==RETURN:
                result=values['rax'] if case==2 else values['rax']&0xffffffff
                mem=dict(values['mem'].entries)
                return {'status':'RETURN','result':result,'memory':[mem.get(STORAGE+i,values['mem'].default) for i in range(32)],'trace':trace}
            enabled=[e for e in self.edges.get(pc,[]) if eval_expr(e[1],state)]
            if len(enabled)!=1:
                return {'status':'AMBIGUOUS' if enabled else 'STUCK','pc':pc,'enabled':len(enabled),'trace':trace}
            edge,_,update=enabled[0]
            trace.append({'pc':pc,'outcome':edge.id.outcome.value})
            if edge.summary.target.kind in ('error','halt','stuck'):
                return {'status':edge.summary.target.kind.upper(),'pc':pc,'trace':trace}
            state=eval_update(update,state)
        return {'status':'STEP_LIMIT','trace':trace}
