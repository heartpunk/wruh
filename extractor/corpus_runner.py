"""Bounded concrete execution of extracted local edges using AYXG semantics."""
from __future__ import annotations
from ayxg.expr import Declaration
from ayxg.qfabv import (ArraySort, BoolSort, QFAbvArrayValue, QFAbvContext,
                       QFAbvExpr, QFAbvUpdate, QFAbvValuation, decode_sort)
from ayxg.eval import eval_expr, eval_update
from extractor.artifact import LocalEdge
from extractor.architecture import ArchitectureLayout, NORMALIZED_AMD64_FLAGS

STORAGE = 0x100000
STACK = 0x200008  # SysV function entry: rsp mod 16 = 8.
RETURN = 0x300000

class CorpusRunner:
    def __init__(self, model: dict):
        self.context = QFAbvContext(tuple(Declaration.from_data(d) for d in model['declarations']))
        self.entry = model['entry']
        raw_layout = model.get('architecture')
        self.architecture = ArchitectureLayout.from_data(raw_layout) if raw_layout is not None else None
        # Old fixtures carry only the explicitly projected GPR/flag state. Do
        # not describe their absent architectural fields as full-state coverage.
        self.state_coverage = 'architecture' if self.architecture is not None else 'legacy-projection'
        self.pc_name = self.architecture.ip_view if self.architecture is not None else 'rip'
        self.sp_name = self.architecture.sp_view if self.architecture is not None else 'rsp'
        if self.architecture is not None:
            expected = ({s.name for s in self.architecture.storage} - NORMALIZED_AMD64_FLAGS |
                        {f'rflags_{n}' for n in ('CF','ZF','SF','OF','PF','AF')} | {'mem'})
            if expected != {d.name for d in self.context.declarations}:
                raise ValueError('architecture metadata/declaration domain disagreement')
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
        values.update({self.pc_name:self.entry,self.sp_name:STACK})
        if self.architecture is not None:
            # Harness-model initial state, not a claim about unobserved native
            # register contents. Existing comparisons observe RAX and storage.
            values.update(d=1, ftop=0, fpround=0, sseround=0)
        if case==0:values.update(rdi=STORAGE+4*a,rsi=STORAGE+4*b,rdx=x)
        elif case==1:values.update(rdi=STORAGE+a,rsi=x)
        elif case==2:values.update(rdi=x,rsi=initial)
        else:raise ValueError('case outside harness domain')
        values['mem']=QFAbvArrayValue(ArraySort(64,8),0,tuple(sorted((k,v) for k,v in memory.items() if v)))
        state=QFAbvValuation(self.context,tuple(values[d.name] for d in self.context.declarations))
        trace=[]
        for _ in range(limit):
            values=dict(zip((d.name for d in self.context.declarations),state.values))
            pc=values[self.pc_name]
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
