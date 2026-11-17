"""Verify delivered files, unchanged historical evidence, all saved states and new UCI result."""
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import unquote,urlsplit
import argparse
import hashlib
import json
import sys
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scripts.project_state import load_state,validate_state,summarize_state

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def pdf_check(path):
    reader=PdfReader(path)
    links=[]
    for n,page in enumerate(reader.pages,1):
        assert len(page.extract_text())>100, 'Empty/unreadable PDF page'
        for ref in page.get('/Annots',[]):
            action=ref.get_object().get('/A',{})
            target=action.get('/URI')
            spec=action.get('/F')
            if spec:
                target=spec.get('/UF',spec.get('/F')) if hasattr(spec,'get') else spec
            if not isinstance(target,str): continue
            parts=urlsplit(target)
            if not parts.scheme and not parts.netloc and parts.path:
                relative=target if spec else unquote(parts.path)
                assert (path.parent/relative).is_file(), (path,n,target)
                links.append({'page':n,'target':target})
    assert len(reader.pages)==5
    assert len(links)>10, 'Missing relative navigation'
    return {'sha256':sha(path),'pages':len(reader.pages),'verified_local_links':len(links),'links':links}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--standalone',type=Path)
    args=parser.parse_args()
    report={'at':datetime.now(timezone.utc).isoformat(),'states':{},'runtime_unchanged':True}
    manifest=ROOT/'MANIFEST.json'
    if manifest.exists():
        entries=json.loads(manifest.read_text(encoding='utf-8'))['files']
        assert all((ROOT/x['path']).stat().st_size==x['bytes'] and sha(ROOT/x['path'])==x['sha256'] for x in entries)
        report['manifest_files_verified']=len(entries)
    expected=json.loads((ROOT/'evaluation/task07/expected-final.json').read_text(encoding='utf-8'))
    for name,wanted in expected['states'].items():
        project=ROOT/name
        saved=load_state(project)
        assert (saved['revision'],saved['state_sha256'])==(wanted['revision'],wanted['state_sha256'])
        history=[]
        for path in sorted((project/'state/history').glob('r*.json')):
            old=json.loads(path.read_text(encoding='utf-8'))
            validate_state(project,old,require_saved=True)
            history.append(old['revision'])
        assert summarize_state(project)['summary']['state_sha256']==saved['state_sha256']
        report['states'][name]={'revision':saved['revision'],'state_sha256':saved['state_sha256'],'history_valid':history}
    protected=json.loads((ROOT/'evaluation/public-data-release/preserved-before.json').read_text(encoding='utf-8'))
    packaged={name:digest for name,digest in protected.items() if not name.startswith('dist/')}
    assert all(sha(ROOT/name)==digest for name,digest in packaged.items())
    report['preserved_files_verified']=len(packaged)
    proof=json.loads((ROOT/'evaluation/provenance-release/continuation-result.json').read_text(encoding='utf-8'))
    resumed_project=ROOT/'evaluation/provenance-release/continuation-workspace/projects/task06-rehearsal'
    resumed=load_state(resumed_project)
    assert (resumed['revision'],resumed['state_sha256'])==(proof['revision'],proof['state_sha256'])
    assert all(sha(ROOT/name)==digest for name,digest in proof['runtime'].items())
    assert all(sha(resumed_project/item['path'])==item['sha256'] for item in proof['new_artifacts'])
    report['independent_continuation']={'revision':resumed['revision'],'new_artifacts_verified':len(proof['new_artifacts']),
        'runtime_matches':True,'new_llm_run':False,'scope':'one useful analytical step'}
    project=ROOT/'evaluation/public-data-release/projects/uci-shoppers'
    state=load_state(project)
    assert state['revision']==1 and state['decision']['status']=='awaiting_decision'
    calc=json.loads((project/'evidence/calculations/independent-v1.json').read_text(encoding='utf-8'))
    assert calc['rows']==12330 and calc['groups_checked']==23 and calc['all_calculator_groups_match']
    assert sha(project/'inputs/online_shoppers_intention.csv')=='b3055ee355f59134d851d32641183cb4a8b45def7124d2f50442a042f358e0d9'
    report['uci']={'revision':1,'state_sha256':state['state_sha256'],'rows':calc['rows'],'revenue':calc['revenue'],'groups_checked':23}
    strategies=json.loads((ROOT/'submission/strategies/sources.json').read_text(encoding='utf-8'))
    assert all(sha(ROOT/item['path'])==item['sha256'] for section in strategies.values() if isinstance(section,list) for item in section)
    report['reader_strategy_sources_unchanged']=True
    report['pdf']=pdf_check(ROOT/'submission/Описание проекта.pdf')
    if args.standalone: report['standalone_pdf']=pdf_check(args.standalone)
    assert sha(ROOT/'submission/video/Демонстрация.mp4')=='243e78d1c5dfe54073f817b53f9669f608f896fc7ac084e08c72ded332b3e8db'
    report['video_unchanged']=True
    report['passed']=True
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
    print(json.dumps({k:v for k,v in report.items() if k not in ('pdf','standalone_pdf','states')},ensure_ascii=False))

if __name__=='__main__': main()
