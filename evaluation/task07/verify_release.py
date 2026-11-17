"""Check the exact extracted candidate with its offline runtime; no LLM calls."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,importlib.metadata,json,re,struct,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scripts.project_state import load_state,validate_state
from pypdf import PdfReader
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--output',type=Path,required=True);args=a.parse_args()
    assert sys.prefix!=sys.base_prefix,'Fresh virtual environment required'
    expected=json.loads((ROOT/'evaluation/task07/expected-final.json').read_text(encoding='utf-8'))
    manifest=json.loads((ROOT/'MANIFEST.json').read_text(encoding='utf-8'))
    mismatches=[x['path'] for x in manifest['files'] if sha(ROOT/x['path'])!=x['sha256']]
    assert not mismatches,mismatches
    checks={'manifest_files':len(manifest['files']),'manifest_unchanged':True,
      'python':sys.version,'isolated_environment':True,
      'dependencies':{p:importlib.metadata.version(p) for p in ('openpyxl','pypdf','et-xmlfile')},'states':{}}
    for name,wanted in expected['states'].items():
        p=ROOT/name;s=load_state(p)
        assert s['revision']==wanted['revision'] and s['state_sha256']==wanted['state_sha256'],name
        history=[]
        for f in sorted((p/'state/history').glob('r*.json')):
            h=json.loads(f.read_text(encoding='utf-8'));validate_state(p,h,require_saved=True);history.append(h['revision'])
        checks['states'][name]={'revision':s['revision'],'history_valid':history,'decision_status':s['decision']['status']}
    p=ROOT/'evaluation/task07/demo-workspace/projects/task06-rehearsal';s=load_state(p)
    assert s['evaluation']['synthetic'] is True
    assert len(s['decision']['history'])>=1 and s['decision']['status']=='simulated_accepted'
    assert s['decision']['commitments'] and s['decision']['metrics'] and s['decision']['conditions']
    assert all(c['status']!='completed' or c.get('completion_evidence') for c in s['decision']['commitments'])
    assert any(r['owner_review_required'] for r in s['decision']['reviews'])
    assert set(s['decision']['current_outputs'])=={'situation','options','product-strategy','communication-strategy','validation-plan'}
    r7=json.loads((p/'state/history/r000007.json').read_text(encoding='utf-8'))
    assert s['decision']['history']==r7['decision']['history'],'Original decision was rewritten'
    old_art={x['id']:x for x in r7['artifacts']};new_art={x['id']:x for x in s['artifacts']}
    assert new_art['FUNNEL_CALC']==old_art['FUNNEL_CALC'],'Unaffected funnel changed'
    assert all(c['status'] in ('pending','blocked') for c in s['decision']['commitments'])
    change=json.loads((p/'evidence/support-change-check-v1.json').read_text(encoding='utf-8'))
    assert change['changed_cells']==[['Экономика','E3',30,90]]
    from fractions import Fraction
    base=change['calculation_base'];contribution=Fraction(3000)-600-Fraction(90,60)*600
    assert Fraction(base['margin_rub_per_account_month'])==contribution==1500
    assert Fraction(base['surplus_before_unknown_costs_rub_month'])==20*contribution-30000==0
    assert base['min_accounts_positive']==21 and base['conditional_setup_payback_months'] is None
    checks['followup']={'original_decision_preserved':True,'unaffected_funnel_preserved':True,
       'changed_cells':change['changed_cells'],'independent_fraction_check':True,
       'commitments_unperformed':True,'new_owner_review_required':True}
    proof=json.loads((ROOT/'evaluation/task07/continuation-result.json').read_text(encoding='utf-8'))
    r2=json.loads((p/'state/history/r000002.json').read_text(encoding='utf-8'))
    validate_state(p,r2,require_saved=True)
    assert sha(p/'state/history/r000002.json')==proof['after_files']['projects/task06-rehearsal/state/current.json']
    for art in proof['new_registered_artifacts']:assert sha(p/art['path'])==art['sha256'],art['path']
    checks['independent_continuation']={'thread_id':proof['thread_id'],'revision':2,'result_artifacts_preserved':True,'separate_loader':proof['separate_loader_pass']}
    before=json.loads((ROOT/'evaluation/task07/preservation-before.json').read_text(encoding='utf-8'))['files']
    protected=0
    for name,h in before.items():
        if name.startswith('dist/'):continue # Original archives stay in delivered host history, outside the candidate.
        assert sha(ROOT/name)==h,name;protected+=1
    checks['historical_preservation']={'packaged_files_verified':protected,'original_dist_checked_separately':True}
    pdf=ROOT/'submission/PROJECT_DESCRIPTION.pdf';reader=PdfReader(pdf)
    assert 3<=len(reader.pages)<=5
    text='\n'.join(x.extract_text() or '' for x in reader.pages)
    for bad in ('TASK06','TASK07','NOT_VERIFIED','C008','frozen-v2','РЕДАКТОРУ:','[[SCREENSHOT:'):assert bad not in text,bad
    annots=sum(len(p.get('/Annots',[])) for p in reader.pages);assert annots>0
    checks['pdf']={'pages':len(reader.pages),'link_annotations':annots,'sha256':sha(pdf),'visual_review':'Separate complete page inspection before sealing'}
    for name,h in expected['final_media'].items():assert sha(ROOT/name)==h,name
    checks['final_media']={'hashes':expected['final_media'],'decode_and_visual_evidence':expected['media_evidence']}
    result={'checked_at':datetime.now(timezone.utc).isoformat(),'passed':True,'checks':checks}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps(result,ensure_ascii=False,indent=2))
