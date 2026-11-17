"""Seal LLM-authored draft references with actual hashes; no analysis generation."""
import argparse
import copy
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from scripts.project_state import reference, load_state

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True)
    p.add_argument('--content',required=True);p.add_argument('--output',required=True);p.add_argument('--from-current',action='store_true')
    a=p.parse_args();content=json.loads((a.project/a.content).read_text(encoding='utf-8'))
    draft=copy.deepcopy(load_state(a.project)) if a.from_current else {}
    for field in ('revision','saved_at','state_sha256'):draft.pop(field,None)
    artifact_paths=content.pop('new_artifacts',{})
    new_claims=content.pop('new_claims',[])
    draft.update(content)
    draft.setdefault('artifacts',[]);draft.setdefault('sources',[]);draft.setdefault('claims',[])
    existing={x['id'] for x in draft['artifacts']}
    for sid_dir in sorted((a.project/'evidence/sources').iterdir()):
        for version_dir in sorted(sid_dir.glob('v*')):
            meta=json.loads((version_dir/'source.json').read_text(encoding='utf-8'))
            prefix=f"{meta['id']}v{meta['version']}"
            ids=[]
            for kind,path in [('meta',(version_dir/'source.json').relative_to(a.project).as_posix()),
                              ('original',meta['original']['path']),('extract',meta['extract']['path'])]:
                aid=prefix+'_'+kind;ids.append(aid)
                if aid not in existing:artifact_paths[aid]=path
            if not any(s['id']==meta['id'] and s['version']==meta['version'] for s in draft['sources']):
                draft['sources'].append({'id':meta['id'],'version':meta['version'],'artifact_ids':ids,'synthetic':meta['synthetic']})
    for aid,path in artifact_paths.items():
        if aid in existing:raise ValueError('Existing artifact ID cannot be overwritten: '+aid)
        draft['artifacts'].append(reference(a.project,path,aid))
    draft['claims']+=new_claims
    target=a.project/a.output;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x',encoding='utf-8') as f:json.dump(draft,f,ensure_ascii=False,indent=2)
    print(json.dumps({'draft':a.output,'artifacts':len(draft['artifacts']),'claims':len(draft['claims'])}))
