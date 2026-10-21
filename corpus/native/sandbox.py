"""Fail-closed Linux native harness launcher. Requires explicit approval upstream."""
from __future__ import annotations
import hashlib, json, subprocess, uuid
from pathlib import Path

BWRAP = '/nix/store/qn1pfnn2xgfwdr6avw1fnvwsabi83973-bubblewrap-0.11.0/bin/bwrap'
LIBC = '/nix/store/ias8xacs1h3jy7xgwi2awvim61k2ji6c-glibc-2.42-67'
RUNTIME = (LIBC,
 '/nix/store/dxszpyw0pn7h1cxi1y6l33nmwk7f5knn-libunistring-1.4.2',
 '/nix/store/clqknm3pgln8pxb6n7iamffk313nr91r-libidn2-2.3.8',
 '/nix/store/hps7pxvcgq32x46yx5a2nx53js5j41vb-xgcc-15.2.0-libgcc')
HASHES = {
 '0':'0eb15471007c33d56e3eb001b4b3a1bf17b35d84a073cbf8529ddc5433043bb4',
 '2':'4e6600d82a62fbc350636f52ce863600976e56bbdecca524968181330f33080f',
}

def command(binary: Path, inputs: tuple[int,...], mounts: tuple[str,...] = RUNTIME) -> list[str]:
    cmd=['systemd-run','--user','--quiet','--wait','--pipe','--collect',
         '--unit=wruh-native-'+uuid.uuid4().hex,
         '-p','MemoryMax=256M','-p','MemorySwapMax=0','-p','CPUQuota=100%',
         '-p','AllowedCPUs=0','-p','TasksMax=64','-p','NoNewPrivileges=yes',
         '-p','RuntimeMaxSec=2s',BWRAP,'--unshare-all','--unshare-user',
         '--disable-userns','--cap-drop','ALL','--clearenv','--setenv','LANG','C',
         '--new-session','--die-with-parent']
    for mount in mounts:cmd += ['--ro-bind',mount,mount]
    return cmd+['--ro-bind',str(binary.resolve()),'/candidate','--proc','/proc',
                '--dev','/dev','--size','1048576','--tmpfs','/tmp','--chdir','/tmp',
                '--','/candidate',*(str(v) for v in inputs)]

def run(binary: Path, optimization: str, inputs: tuple[int,...]) -> dict:
    if hashlib.sha256(binary.read_bytes()).hexdigest()!=HASHES[optimization]:
        raise ValueError('binary differs from approved hash')
    if len(inputs)!=5 or any(type(v) is not int or not 0<=v<=0xffffffff for v in inputs) or inputs[0]>2 or inputs[1]>7 or inputs[2]>7:
        raise ValueError('input outside approved domain')
    cmd=command(binary,inputs)
    try:
        p=subprocess.run(cmd,text=True,capture_output=True,timeout=5)
    except subprocess.TimeoutExpired as exc:
        return {'status':'TIMEOUT','command':cmd,'error':str(exc)}
    result={'command':cmd,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
    if p.returncode:result['status']='EXECUTION_FAILURE';return result
    parts=p.stdout.split()
    if len(parts)!=33:result['status']='INVALID_OUTPUT';return result
    try:
        value=int(parts[0]);memory=[int(s,16) for s in parts[1:]]
        if not 0<=value<1<<64 or any(not 0<=b<256 for b in memory):raise ValueError()
    except ValueError:result['status']='INVALID_OUTPUT';return result
    result.update(status='RETURN',result=value,memory=memory)
    return result
