"""Verify an extracted release using only the pinned agent runtime and stdlib."""
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import struct
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scripts.project_state import load_state,validate_state
from evaluation.check_m2_fidelity import verify as fidelity
from evaluation.check_offer_arithmetic import check as arithmetic
from pypdf import PdfReader

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();checks={}
    manifest=json.loads((ROOT/'MANIFEST.json').read_text(encoding='utf-8'))
    mismatch=[x['path'] for x in manifest['files'] if sha(ROOT/x['path'])!=x['sha256']]
    assert not mismatch,mismatch
    checks['manifest_after_execution']={'files':len(manifest['files']),'changed':mismatch}
    checks['python']={'version':sys.version,'executable':sys.executable,'prefix':sys.prefix,'base_prefix':sys.base_prefix,
        'dependencies':{p:importlib.metadata.version(p) for p in ('openpyxl','pypdf','et-xmlfile')}}
    assert sys.prefix!=sys.base_prefix
    checks['states']={}
    for name,expected in [('demo-001',5),('demo-002',5),('task06-rehearsal',6)]:
        p=ROOT/'projects'/name;s=load_state(p);assert s['revision']==expected
        revisions=[]
        for f in sorted((p/'state/history').glob('r*.json')):
            historical=json.loads(f.read_text(encoding='utf-8'));validate_state(p,historical,require_saved=True);revisions.append(historical['revision'])
        checks['states'][name]={'revision':s['revision'],'stage':s['stage'],'decision':s['decision']['status'],
            'history_valid':revisions,'state_sha256':s['state_sha256']}
    project=ROOT/'projects/task06-rehearsal'
    checks['fidelity']={str(v):{'passed':(r:=fidelity(project,v))['passed'],'checks':len(r['checks'])} for v in (1,2)}
    checks['arithmetic']={str(v):{'passed':(r:=arithmetic(project,v))['passed'],'checks':len(r['checks'])} for v in (1,2)}
    handoff=ROOT/'evaluation/task06/continuation-workspace'
    frozen=json.loads((ROOT/'evaluation/task06/continuation-manifest.json').read_text(encoding='utf-8'))
    assert load_state(handoff/'projects/task06-rehearsal')['revision']==1
    assert not (handoff/'projects/task06-rehearsal/outputs').exists()
    with zipfile.ZipFile(ROOT/'evaluation/task06/continuation-checkpoint.zip') as z:
        assert z.testzip() is None
        assert set(z.namelist())=={f['path'] for f in frozen['files']}
        for f in frozen['files']:
            assert sha(handoff/f['path'])==f['sha256']==hashlib.sha256(z.read(f['path'])).hexdigest()
    checks['handoff']={'revision':1,'unchanged_files':len(frozen['files']),'outputs_absent':True,
        'independent_llm_run':'NOT_VERIFIED'}
    pdf=ROOT/'submission/PROJECT_DESCRIPTION.pdf';reader=PdfReader(pdf)
    text='\n'.join(p.extract_text() for p in reader.pages)
    for term in ['TASK06_LOCAL_PACKAGE_WITH_GAPS','1500','1207.712457','VIDEO_NOT_RECORDED','725.113674']:
        assert term in text,term
    annotation_count=sum(len(p.get('/Annots',[])) for p in reader.pages)
    assert annotation_count>0
    screenshots=[]
    for name in ['source-brief-p02.png','result-v2-fixed-p01.png','followup-r6-fixed-p01.png']:
        f=ROOT/'submission/screenshots'/name;data=f.read_bytes();assert data[:8]==b'\x89PNG\r\n\x1a\n'
        width,height=struct.unpack('>II',data[16:24]);assert width>=900 and height>=1200
        screenshots.append({'path':f.relative_to(ROOT).as_posix(),'width':width,'height':height,'sha256':sha(f)})
    checks['description']={'pages':len(reader.pages),'annotations':annotation_count,'sha256':sha(pdf),
        'screenshots':screenshots,'layout_review':'Separate visual review of actual export; this check verifies packaged bytes/text/annotations.'}
    frozen_ab=json.loads((ROOT/'evaluation/task06/ordinary-freeze-manifest.json').read_text(encoding='utf-8'))
    for path,digest in frozen_ab['files'].items():assert sha(ROOT/'evaluation/task06/ordinary-current-v1'/path)==digest
    checks['ordinary_freeze']={'files':len(frozen_ab['files']),'status':'NOT_RUN'}
    before=json.loads((ROOT/'evaluation/task06/preservation-before.json').read_text(encoding='utf-8'))['files']
    for path,digest in before.items():assert sha(ROOT/path)==digest,path
    checks['historical_preservation']={'files':len(before),'passed':True}
    result={'observed_at':datetime.now(timezone.utc).isoformat(),'root':str(ROOT),'passed':True,'checks':checks}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps(result,ensure_ascii=False,indent=2))
