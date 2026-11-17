"""Структурные ссылки пяти outputs; смысл отдельно проверяет evidence-review."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.project_state import load_state


def verify(project, version):
    state=load_state(project);claims={c['id']:c for c in state['claims']}
    artifacts={a['path']:a for a in state['artifacts']};checks=[]
    for name in ('situation','options','product-strategy','communication-strategy','validation-plan'):
        rel=f'outputs/{version}/{name}.md';text=(project/rel).read_text(encoding='utf-8')
        if rel not in artifacts:raise ValueError('Output not pinned: '+rel)
        used=set(re.findall(r'\bC\d{3}\b',text))
        if not used:raise ValueError('No claim references: '+rel)
        for cid in used:
            if cid not in claims:raise ValueError('Unknown claim: '+cid)
            if claims[cid].get('status')=='superseded':raise ValueError('Superseded claim in current output: '+cid)
        checks.append({'path':rel,'claim_ids':sorted(used),'pinned':True})
    return {'checked_at':datetime.now(timezone.utc).isoformat(),'revision':state['revision'],'checks':checks,'semantic_truth_checked':False}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--version',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=verify(a.project,a.version)
    a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'outputs_checked':len(r['checks']),'state_revision':r['revision'],'semantics':'separate_review'}))
