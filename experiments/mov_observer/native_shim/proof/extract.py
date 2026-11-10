from pathlib import Path
import hashlib, sys
root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(root))
from extractor import runtime
from extractor import amd64_state as amd
import z3
base = 0x400000
blob = (Path(__file__).resolve().parents[1] / 'evidence/shim.bin').read_bytes()
assert hashlib.sha256(blob).hexdigest() == '318c587381ddd44658b17e8c40b4b80a857989da16581ec7aa546a4e157f982a'
project = runtime.angr.load_shellcode(blob, arch='amd64', load_address=base)
out = Path(sys.argv[1]); out.mkdir(exist_ok=True)
assert len(blob) == 65 and blob[58:60] == bytes.fromhex('0f05')
system_call = project.factory.block(base+58, size=2, num_inst=1)
assert system_call.size == 2 and system_call.instructions == 1
assert system_call.vex.jumpkind == 'Ijk_Sys_syscall'
(out/'syscall.txt').write_text(str(system_call.capstone)+'\n'+str(system_call.vex)+'\n')
for label, offset, length, count in [('prefix',0,58,13), ('suffix',60,5,2)]:
    block = project.factory.block(base+offset, size=length, num_inst=count)
    assert block.size == length and block.instructions == count
    assert block.vex.jumpkind == ('Ijk_Boring' if label == 'prefix' else 'Ijk_Ret')
    state = amd.fresh_instruction_state(project,base+offset)
    states = project.factory.successors(state,size=length,num_inst=count).all_successors
    assert len(states)==1, (label,len(states))
    post=states[0]; post.globals['_wruh_capture_selectors']=False
    updates=amd._post_updates(post,base+offset)
    amd._symbolic_target_update(post,updates)
    updates['mem']=z3.simplify(amd._resolve_memory_reads(post.globals['_ghot_memory_expr'], post.globals['_ghot_memory_reads']))
    (out/f'{label}.txt').write_text(str(block.capstone)+'\n'+str(block.vex)+'\n'+ '\n'.join(f'{k}: {z3.simplify(v).sexpr()}' for k,v in updates.items()))
    print(label, 'constraints',post.solver.constraints, 'updates',list(updates),flush=True)

# Emit the actual canonical updates as typed AYXG expressions. Unsupported
# expressions abort export; every canonical state field is retained.
names = ['mem','rip',*['rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi','r8','r9','r10','r11','r12','r13','r14','r15']]
names += [d.name for d in amd.canonical_declarations() if d.name not in names]
lines=['-- Exact shim SHA256 '+hashlib.sha256(blob).hexdigest(), 'import Extracted',
       'set_option maxRecDepth 32768', 'set_option maxHeartbeats 4000000',
       'namespace MovObserver.Shim', 'open Ayxg.QfAbv']
cache={}
def sort(e):
    if z3.is_bv(e): return f'(.bv {e.size()})'
    if z3.is_bool(e): return '.bool'
    return '(.array 64 8)'
def emit(e):
    key=e.sexpr()
    if key in cache:return cache[key]
    k=e.decl().kind(); args=[emit(a) for a in e.children()]
    if z3.is_bv_value(e): body=f'.bvLit {e.size()} {e.as_long()}'
    elif z3.is_true(e) or z3.is_false(e): body=f'.boolLit {str(z3.is_true(e)).lower()}'
    elif k==z3.Z3_OP_UNINTERPRETED:
        assert str(e) in names, str(e)
        body=f'.var v_{e}'
    elif k in (z3.Z3_OP_BADD,z3.Z3_OP_BSUB,z3.Z3_OP_BAND,z3.Z3_OP_BOR,z3.Z3_OP_BXOR):
        op={z3.Z3_OP_BADD:'add',z3.Z3_OP_BSUB:'sub',z3.Z3_OP_BAND:'and',z3.Z3_OP_BOR:'or',z3.Z3_OP_BXOR:'xor'}[k]
        body=args[0]
        for a in args[1:]:body=f'(.bvBin .{op} {e.size()} {body} {a})'
    elif k==z3.Z3_OP_BNOT: body=f'.bvNot {e.size()} {args[0]}'
    elif k==z3.Z3_OP_ITE:body=f'.ite {args[0]} {args[1]} {args[2]}'
    elif k==z3.Z3_OP_EQ:body=f'.eqBv {e.arg(0).size()} {args[0]} {args[1]}'
    elif k==z3.Z3_OP_ULEQ:body=f'.bvUle {e.arg(0).size()} {args[0]} {args[1]}'
    elif k==z3.Z3_OP_SELECT:body=f'.select 64 8 {args[0]} {args[1]}'
    elif k==z3.Z3_OP_STORE:body=f'.store 64 8 {args[0]} {args[1]} {args[2]}'
    elif k==z3.Z3_OP_EXTRACT:
        hi,lo=e.decl().params();body=f'.extract {{hi := {hi}, lo := {lo}, hi_lt_width := by decide, lo_le_hi := by decide}} {args[0]}'
    elif k==z3.Z3_OP_CONCAT:
        body=args[0]; width=e.arg(0).size()
        for a,term in zip(e.children()[1:],args[1:]):
            body=f'(.concat {width} {a.size()} {body} {term})'; width+=a.size()
    else:raise ValueError(e.sexpr())
    name=f'e{len(cache)}'; cache[key]=name
    lines.append(f'def {name} : Expr Γ {sort(e)} := {body}')
    return name
for label, offset, length, count in [('prefix',0,58,13), ('suffix',60,5,2)]:
    state=amd.fresh_instruction_state(project,base+offset)
    successors=project.factory.successors(state,size=length,num_inst=count).all_successors
    assert len(successors)==1
    post=successors[0]; assert not post.solver.constraints
    post.globals['_wruh_capture_selectors']=False
    updates=amd._post_updates(post,base+offset); amd._symbolic_target_update(post,updates)
    updates['mem']=z3.simplify(amd._resolve_memory_reads(post.globals['_ghot_memory_expr'], post.globals['_ghot_memory_reads']))
    exprs={k:emit(z3.simplify(v)) for k,v in updates.items()}
    update='.nil'
    for name in reversed(names): update=f'(.cons {exprs.get(name,f"(.var v_{name})")}\n {update})'
    lines.append(f'def {label}Update : StateUpdate Γ Γ := {update}')
    lines.append(f'def {label}Step : QFAbvStep Γ Γ := ⟨.eqBv 64 (.var v_rip) (.bvLit 64 {base+offset}), {label}Update⟩')
    if label == 'prefix': lines.append('variable [FPInterpretation]')
    for name in names:
        expr=exprs.get(name,f'(.var v_{name})')
        lines.append(f'theorem {label}_{name} (s : Env Γ) : Env.lookup ({label}Update.eval s) v_{name} = Eval.eval s {expr} := rfl')
    if label=='prefix':
        memory=updates['mem']; ws=[]; byte_events=[]
        while memory.decl().kind()==z3.Z3_OP_STORE:
            byte_events.append((memory.arg(1),memory.arg(2)))
            ws.append((emit(memory.arg(1)),emit(memory.arg(2))));memory=memory.arg(0)
        assert str(memory)=='mem' and len(ws)==32
        ws.reverse(); byte_events.reverse()
        writes = amd._resolved_writes(post)
        assert len(writes) == 4 and all(w.size == 8 for w in writes)
        expanded = [(z3.simplify(w.address+i), z3.simplify(z3.Extract(8*i+7,8*i,w.value)))
                    for w in writes for i in range(w.size)]
        assert all(z3.is_true(z3.simplify(a == b)) and
                   z3.is_true(z3.simplify(v == u))
                   for (a,v),(b,u) in zip(byte_events,expanded))
        (out/'write-events.txt').write_text('\n'.join(
            f'{i}: address={z3.simplify(w.address).sexpr()} size={w.size} value={z3.simplify(w.value).sexpr()}'
            for i,w in enumerate(writes))+'\n')
        lines.append('def prefixWrites : List (Expr Γ (.bv 64) × Expr Γ (.bv 8)) := ['+',\n'.join(f'({a},{v})' for a,v in ws)+']')
        print('prefix word writes', [(str(z3.simplify(w.address)), w.size) for w in writes])
    else:
        assert not amd._resolved_writes(post)
lines.append('end MovObserver.Shim')
(out/'ShimModel.lean').write_text('\n'.join(lines)+'\n')
print('emitted',len(cache),'expression nodes')
