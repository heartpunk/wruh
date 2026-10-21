import importlib.util,json,pathlib,subprocess
spec=importlib.util.spec_from_file_location('sandbox','/tmp/wruh-sandbox.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
ns={n:str(pathlib.Path('/proc/self/ns/'+n).stat().st_ino) for n in ['user','net','pid','mnt']}
script='''import os,json,pathlib,socket,sys
host=json.loads(sys.argv[1]); observed={n:str(pathlib.Path('/proc/self/ns/'+n).stat().st_ino) for n in host}
assert all(observed[n]!=host[n] for n in host)
status=pathlib.Path('/proc/self/status').read_text()
assert 'NoNewPrivs:\\t1' in status
assert 'CapEff:\\t0000000000000000' in status
assert not pathlib.Path('/home').exists()
assert not pathlib.Path('/Users').exists()
assert os.listdir('/sys/class/net')==[] if pathlib.Path('/sys/class/net').exists() else True
assert len(socket.if_nameindex())==1 and socket.if_nameindex()[0][1]=='lo'
mounts=[line.split() for line in pathlib.Path('/proc/self/mountinfo').read_text().splitlines()]
assert any(row[4]==sys.argv[2] and 'ro' in row[5].split(',') for row in mounts)
assert any(row[4]=='/candidate' and 'ro' in row[5].split(',') for row in mounts)
p=pathlib.Path(sys.argv[2])/'wruh-write-test'
try:p.write_text('forbidden')
except OSError:pass
else:raise AssertionError('runtime writable')
pathlib.Path('/tmp/test').write_text('ok')
print(json.dumps({'namespace_isolation':True,'no_new_privileges':True,'capabilities_zero':True,'network_interfaces':socket.if_nameindex(),'runtime_readonly':True,'home_absent':True,'temporary_storage_writable':True}))
'''
closure=tuple(pathlib.Path('/tmp/wruh-trusted-python-closure.txt').read_text().splitlines())
cmd=m.command(pathlib.Path('/nix/store/m1fw8l8y9ycxh5dzispbb7cwl6rra14l-python3-3.13.12/bin/python3.13'),('-c',script,json.dumps(ns),m.LIBC),tuple(sorted(set(closure+m.RUNTIME))))
cmd.remove('--collect');cmd.insert(1,'--remain-after-exit')
import select
unit=next(v.split('=',1)[1] for v in cmd if v.startswith('--unit='))
p=subprocess.Popen(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
try:
    if not select.select([p.stdout],[],[],3)[0]:raise RuntimeError('trusted probe produced no result')
    line=p.stdout.readline()
    limits=subprocess.check_output(['systemctl','--user','show',unit,'-p','MemoryMax','-p','MemorySwapMax','-p','CPUQuotaPerSecUSec','-p','AllowedCPUs','-p','TasksMax','-p','NoNewPrivileges','-p','RuntimeMaxUSec'],text=True)
finally:
    subprocess.run(['systemctl','--user','stop',unit],check=True)
out,err=p.communicate(timeout=3)
print(json.dumps({'command':cmd,'exit':p.returncode,'stdout':line+out,'stderr':err,'effective_service_limits':limits},indent=2));raise SystemExit(p.returncode)
