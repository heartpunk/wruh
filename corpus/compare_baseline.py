import json
from pathlib import Path


def norm(v):
 if isinstance(v,list):return [norm(x) for x in v]
 if not isinstance(v,dict):return v
 v={k:norm(x) for k,x in v.items()}
 if v.get('op')=='bv_ule' and v['args'][1].get('op')=='bv_lit' and v['args'][1]['value']==(1<<v['args'][1]['sort']['width'])-1:return {'op':'bool_lit','sort':{'kind':'bool'},'value':True}
 if v.get('op')=='bool_not' and v['args'][0].get('op')=='bool_not':return v['args'][0]['args'][0]
 if v.get('op')=='bool_and':
  a=[]
  for x in v['args']:
   if x.get('op')=='bool_lit' and x['value']:continue
   a.extend(x['args'] if x.get('op')=='bool_and' else [x])
  if not a:return {'op':'bool_lit','sort':{'kind':'bool'},'value':True}
  if len(a)==1:return a[0]
  v['args']=sorted(a,key=lambda x:json.dumps(x,sort_keys=True))
 return v
if __name__ == '__main__':
 import argparse
 parser=argparse.ArgumentParser()
 parser.add_argument('baseline',type=Path);parser.add_argument('current',type=Path)
 args=parser.parse_args();results=[]
 for p in sorted(args.baseline.glob('corpus_extract_*.json')):
  if 'runtime-trace' in p.name:continue
  a=json.loads(p.read_text());b=json.loads((args.current/p.name).read_text())
  if a['status']!='PASS':continue
  equal=b['status']=='PASS' and a['elf_sha256']==b['elf_sha256'] and norm(a['fresh_model'])==norm(b['fresh_model'])
  results.append({'case':p.stem,'preserved':equal,'baseline_edges':a['local_edges'],'current_edges':b.get('local_edges')})
 print(json.dumps({'method':'Exact equality after unsigned-BV maximum tautology, conjunction identities, and double-negation elimination; no approximate normalization.', 'cases':results,'preserved':sum(r['preserved'] for r in results),'total':len(results)},indent=2))
 raise SystemExit(0 if results and all(r['preserved'] for r in results) else 1)
