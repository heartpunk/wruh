"""Static-only zeroth-pass compiler, VEX feature collector, and fresh extractor."""
from __future__ import annotations
import argparse, base64, hashlib, json, os, shutil, subprocess, tempfile, time
from pathlib import Path
from extractor.runtime_trace import start_runtime_trace
start_runtime_trace()
from extractor import runtime as _runtime
import angr
from extractor.instruction_inventory import inventory_project
from extractor.loaded_image import load_object_set
from extractor.fresh import extract_linear, linear_site_records

CANONICAL = ['var','bool_lit','bv_lit','bool_not','bool_and','bool_or','ite','bv_add','bv_sub','bv_mul','bv_udiv','bv_urem','bv_and','bv_or','bv_xor','bv_shl','bv_lshr','bv_ashr','bv_ult','bv_ule','bv_slt','bv_sle','eq','bv_not','zero_extend','sign_extend','extract','concat','const_array','select','store']
CONTROL = {'jump:Ijk_Call','jump:Ijk_Ret'}

def features(project, decoded):
    found = set()
    failures = []
    for instruction in decoded.decoded:
        try:
            ir = project.factory.block(instruction.address, num_inst=1).vex
            found.add('jump:' + ir.jumpkind)
            for stmt in ir.statements:
                found.add('stmt:' + stmt.tag)
                if stmt.tag == 'Ist_Store':
                    found.add('store:' + str(stmt.data.result_size(ir.tyenv)) + ':' + stmt.end)
            for expr in ir.expressions:
                found.add('expr:' + expr.tag)
                if hasattr(expr, 'op'): found.add('vex:' + expr.op)
                if expr.tag == 'Iex_Load':
                    found.add('load:' + str(expr.result_size(ir.tyenv)) + ':' + expr.end)
        except Exception as error:
            failures.append({'address': instruction.address, 'error': str(error)})
    return sorted(found), failures

def scan(args):
    compiler=shutil.which('clang')
    if compiler is None:raise RuntimeError('declared runtime clang unavailable')
    version=subprocess.check_output([compiler,'--version'],text=True)
    command=[compiler, '-O'+args.optimization,'-fno-inline','-fno-builtin','-fno-stack-protector','-fno-vectorize','-fno-slp-vectorize','-nostdlib','-no-pie','-Wl,-e,arithmetic',*args.source]
    with tempfile.TemporaryDirectory() as temp:
        elf=Path(temp)/'corpus.elf'
        subprocess.run(command+['-o',str(elf)],check=True)
        project=load_object_set(elf)
        decoded=inventory_project(project)
        observed_features, feature_failures = features(project, decoded)
        candidates={'image': {'features': observed_features}}
        from angr.engines.vex.claripy import irop
        registry=set(irop.operations)
        observed=set().union(*(set(c['features']) for c in candidates.values()))
        selection_universe={f for f in observed if not f.startswith('vex:') or f[4:] in registry}|CONTROL
        remaining=set(selection_universe);pool=set(candidates);selected=[]
        while pool and remaining:
            name=min(pool,key=lambda n:(-len(set(candidates[n]['features'])&remaining),n))
            gain=set(candidates[name]['features'])&remaining
            if not gain:break
            selected.append({'name':name,'new_features':sorted(gain)})
            remaining-=gain;pool.remove(name)
        return {'optimization':args.optimization,'compiler':version,'command':command+['-o','<temporary>/corpus.elf'],
          'source_sha256':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in args.source},
          'elf_sha256':hashlib.sha256(elf.read_bytes()).hexdigest(),'elf_base64':base64.b64encode(elf.read_bytes()).decode(),
          'candidates':candidates,'selected':selected,'feature_failures':feature_failures,'selection_universe':sorted(selection_universe),'uncovered':sorted(remaining),
          'inherited_vex_registry_count':len(registry),'inherited_vex_registry':sorted(registry),'observed_vex_not_in_registry':sorted(f for f in observed if f.startswith('vex:') and f[4:] not in registry),
          'canonical_required':CANONICAL,'limitations':['VEX selection covers observed supported registry operations, not all inherited angr semantics.','Backend registry membership is availability, not proof of end-to-end WRUH support.','Aliasing input relationships untested.','No native candidate execution.','No FP/vector scope.']}

def prepare_native(args):
    """Compile the audited harness as data; never execute the resulting ELF."""
    compiler=shutil.which('clang')
    if compiler is None:raise RuntimeError('declared runtime clang unavailable')
    command=[compiler, '-O'+args.optimization, '-fno-inline', '-fno-builtin',
             '-fno-stack-protector', '-fno-vectorize', '-fno-slp-vectorize',
             '-no-pie', *args.source]
    with tempfile.TemporaryDirectory() as temp:
        elf=Path(temp)/'native-harness.elf'
        subprocess.run(command+['-o',str(elf)],check=True)
        data=elf.read_bytes()
        project=load_object_set(elf)
        functions={}
        for name in ('main','alias','overlap','division'):
            symbol=project.loader.find_symbol(name)
            block=project.factory.block(symbol.rebased_addr,size=symbol.size)
            functions[name]=str(block.capstone)
        return {'optimization':args.optimization,'command':command+['-o','<temporary>/native-harness.elf'],
                'compiler':subprocess.check_output([compiler,'--version'],text=True),
                'source_sha256':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in args.source},
                'elf_sha256':hashlib.sha256(data).hexdigest(),'elf_base64':base64.b64encode(data).decode(),
                'disassembly':functions,'native_executed':False}

def native_model(args):
    return extract(args)

def expression_ops(fresh):
    todo=[]
    for edge in fresh.local_edges:
        todo.append(edge.summary.guard)
        todo.extend(a.value for a in edge.summary.simultaneous_update)
        if edge.summary.mirrored_pc is not None:todo.append(edge.summary.mirrored_pc)
        if edge.summary.target.value is not None and hasattr(edge.summary.target.value,'op'):todo.append(edge.summary.target.value)
    seen=set();ops=set()
    while todo:
        node=todo.pop()
        if id(node) in seen:continue
        seen.add(id(node));ops.add(node.op);todo.extend(node.args)
    return sorted(ops),len(seen)

def extract(args):
    scan=json.loads(Path(args.scan).read_text())
    started=time.monotonic()
    with tempfile.TemporaryDirectory() as temp:
        elf=Path(temp)/'corpus.elf';elf.write_bytes(base64.b64decode(scan['elf_base64']))
        project=load_object_set(elf)
        try:
            decoded=inventory_project(project)
            records=linear_site_records(project,decoded,chunk_size=256,seed=0)
            fresh=extract_linear(project,records)
            ops,nodes=expression_ops(fresh)
            return {'root':'image','optimization':scan['optimization'],'status':'PASS','elf_sha256':scan['elf_sha256'],
              'occurrences':len(fresh.occurrences),'local_edges':len(fresh.local_edges),'canonical_ops':ops,'expression_objects':nodes,
              'inventory':{'decoded':len(decoded.decoded),'unresolved':len(decoded.unresolved),'unexamined':len(decoded.unexamined)},
              'fresh_model':fresh.to_data(),'seconds':time.monotonic()-started}
        except Exception as exc:
            import traceback
            return {'root':'image','optimization':scan['optimization'],'status':'FAIL','stage':'inventory/extraction',
                    'error_type':type(exc).__name__,'error':str(exc),'traceback':traceback.format_exc(),'seconds':time.monotonic()-started}

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['scan','extract','prepare-native','native-model'],required=True)
    parser.add_argument('--optimization',choices=['0','2'])
    parser.add_argument('--source',action='append',default=[])
    parser.add_argument('--scan');parser.add_argument('--output',required=True)
    args=parser.parse_args()
    result={'scan':scan,'extract':extract,'prepare-native':prepare_native,'native-model':native_model}[args.mode](args)
    Path(args.output).write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
