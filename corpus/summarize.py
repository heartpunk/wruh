"""Summarize declared zeroth-pass output files without running candidates."""
import argparse
import csv
import json
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('results',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
scans=[json.loads(f.read_text()) for f in sorted(a.results.glob('corpus_scan_O[02].json'))]
rows=[json.loads(f.read_text()) for f in sorted(a.results.glob('corpus_extract_*.json')) if 'runtime-trace' not in f.name]
required=set(scans[0]['canonical_required'])
canonical=set().union(*(set(r.get('canonical_ops',[])) for r in rows))
summary={'pass':sum(r['status']=='PASS' for r in rows),'fail':sum(r['status']=='FAIL' for r in rows),'not_selected':sum(r['status']=='NOT_SELECTED' for r in rows),'canonical_required':sorted(required),'canonical_observed':sorted(canonical),'canonical_uncovered':sorted(required-canonical),'variants':[]}
all_features=sorted(set().union(*(set(s['selection_universe']) for s in scans)))
with (a.output/'coverage.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['optimization','function','selected','extraction_status',*all_features,*['canonical:'+x for x in sorted(required)]])
 for s in scans:
  opt=s['optimization'];selected={r['name'] for r in s['selected']};successful=set();status={r['root']:r for r in rows if r['optimization']==opt}
  for name,c in s['candidates'].items():
   r=status[name];features=set(c['features']);ops=set(r.get('canonical_ops',[]))
   if r['status']=='PASS':successful |= features
   w.writerow([opt,name,name in selected,r['status'],*[int(x in features) for x in all_features],*[int(x in ops) for x in sorted(required)]])
  summary['variants'].append({'optimization':opt,'candidate_count':len(s['candidates']),'selected':[r['name'] for r in s['selected']],'selection_universe_count':len(s['selection_universe']),'uncovered_by_selection':s['uncovered'],'uncovered_after_extraction':sorted(set(s['selection_universe'])-successful),'inherited_registry_count':s['inherited_vex_registry_count'],'observed_registry_misses':s['observed_vex_not_in_registry'],'compiler':s['compiler'],'elf_sha256':s['elf_sha256']})
(a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
lines=['# WRUH zeroth-pass corpus','',f"Extraction: {summary['pass']} PASS, {summary['fail']} FAIL, {summary['not_selected']} unselected.",f"Emitted canonical operation kinds: {len(canonical)}/{len(required)}.",'','## Missing emitted operations','',', '.join(sorted(required-canonical)),'','## Selection and surviving coverage','']
for v in summary['variants']:
 lines += [f"- O{v['optimization']}: {v['candidate_count']} candidates; selected {', '.join(v['selected'])}.",f"  Observed selection universe: {v['selection_universe_count']} features; selection gaps: {v['uncovered_by_selection']}; gaps after failed extraction: {v['uncovered_after_extraction']}."]
lines += ['','## Failures','']
for r in rows:
 if r['status']=='FAIL':lines.append(f"- O{r['optimization']} {r['root']}: {r['error_type']}: {r['error']}")
lines += ['','## Limits and first-pass follow-up','','- No native candidate execution or concrete input fuzzing occurred. Sources/templates are NOT approved for native execution.','- VEX set cover covers the observed seed universe plus explicit CFG requirements; it does not establish exhaustive inherited-angr operation coverage.','- Canonical operation occurrence is not validation of its denotation or value boundaries.','- Fresh instruction models were extracted; path composition and end-to-end semantic comparisons were not performed.','- Aliasing inputs, external ABI models, indirect calls, FP/vector behavior, faults, and shrinking remain untested.','- First follow-up: diagnose division CFG overlap; pin alias/overlap scenarios regardless of feature redundancy; audit selected native harness/input domains; run model-vs-binary input comparisons.','- Retain O0/O2 compiled ELFs and per-root fresh models from the declared JSON outputs.','']
(a.output/'README.md').write_text('\n'.join(lines))
print(json.dumps(summary,indent=2))
