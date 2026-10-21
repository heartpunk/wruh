"""Audited bounded native/STS differential campaign."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import tempfile
import time
from collections import Counter
from pathlib import Path

from hypothesis import Phase, given, seed, settings
from hypothesis import strategies as st
from python.runfiles import runfiles

from corpus.native.sandbox import HASHES, run
from extractor.corpus_runner import CorpusRunner

NAMES=('alias','overlap','division')
BOUNDARIES=(0,1,255,256,65535,65536,0x7fffffff,0xffffffff)

def main(args):
    rf=runfiles.Create()
    args.model=[rf.Rlocation(p) for p in args.model]
    args.binary=[rf.Rlocation(p) for p in args.binary]
    models={}
    for path in args.model:
        data=json.loads(Path(path).read_text())
        if data['status']!='PASS':raise RuntimeError('model extraction incomplete')
        key=(data['optimization'],NAMES.index(data['root']))
        if data['elf_sha256']!=HASHES[key[0]]:raise RuntimeError('model binary hash mismatch')
        models[key]=CorpusRunner(data['fresh_model'])
    records=[];started=time.monotonic()
    with tempfile.TemporaryDirectory() as temp:
        binaries={}
        for path in args.binary:
            data=json.loads(Path(path).read_text());opt=data['optimization'];raw=base64.b64decode(data['elf_base64'])
            if hashlib.sha256(raw).hexdigest()!=HASHES[opt]:raise RuntimeError('native hash mismatch')
            binary=Path(temp)/('harness-O'+opt);binary.write_bytes(raw);binary.chmod(0o500);binaries[opt]=binary
        def check(opt,inputs,phase):
            native=run(binaries[opt],opt,inputs)
            model=models[opt,inputs[0]].run(inputs)
            if native['status']!='RETURN' or model['status']!='RETURN':status='INCOMPLETE'
            elif (native['result'],native['memory'])==(model['result'],model['memory']):status='MATCH'
            else:status='MISMATCH'
            record={'optimization':opt,'inputs':inputs,'phase':phase,'status':status,'native':native,'sts':model}
            records.append(record)
            Path(args.output).write_text(json.dumps({'records':records,'counts':dict(Counter(r['status'] for r in records)),'seed':20261002,'seconds':time.monotonic()-started},indent=2)+'\n')
            if status!='MATCH':raise AssertionError(json.dumps({'optimization':opt,'inputs':inputs,'status':status}))
        def run_generated(opt, case):
            @seed(20261002+case)
            @settings(max_examples=64,deadline=None,database=None,phases=(Phase.generate,Phase.shrink))
            @given(a=st.integers(0,7),b=st.integers(0,7),x=st.integers(0,0xffffffff),initial=st.integers(0,0xffffffff))
            def generated(a,b,x,initial):check(opt,(case,a,b,x,initial),'hypothesis')
            generated()
        for opt in ('0','2'):
            for x in BOUNDARIES:
                for a,b in ((0,0),(0,7),(7,7),(7,0)):check(opt,(0,a,b,x,0xffffffff),'deterministic')
                for a in (0,1,7):check(opt,(1,a,0,x,0x12345678),'deterministic')
                for divisor in (0,1,3,0xffffffff):check(opt,(2,0,0,x,divisor),'deterministic')
            for case in range(3):
                run_generated(opt, case)
    print(json.dumps({'counts':dict(Counter(r['status'] for r in records)),'seconds':time.monotonic()-started}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--model',action='append',required=True);parser.add_argument('--binary',action='append',required=True);parser.add_argument('--output',required=True)
    main(parser.parse_args())
