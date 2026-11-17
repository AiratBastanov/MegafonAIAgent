"""Publish only explicitly authored TASK06 evidence-change data through existing helpers."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from scripts.project_state import reference, save_state
from scripts.decision_followup import apply_event

p=Path('projects/task06-rehearsal')
draft=json.loads((p/'drafts/correction-input-v4.json').read_text(encoding='utf-8'))
event={'id':'EV_SUPPORT90','project_id':'task06-rehearsal','kind':'evidence_change',
       'at':datetime.now(timezone.utc).isoformat(),
       'provenance':{'kind':'source_material','artifact_id':'CORRECTION_REQUEST','locator':'учебный шаг коррекции'},
       'change':{'type':'corrected_value','source':{'id':'S002','version':1},'replacement':{'id':'S002','version':2},
                 'locators':["'Экономика'!E3"],'reason':'Новое синтетическое допущение поддержки: 30 -> 90 минут',
                 'old_ground':'30 минут поддержки на организацию в месяц','new_ground':'90 минут, не новое рыночное измерение',
                 'applicability':'Экономика исходящего сценария агентств; воронка/функции не менялись'}}
folder=p/'evidence/events';folder.mkdir(exist_ok=True)
with (folder/'support90-v1.json').open('x',encoding='utf-8') as f:json.dump(event,f,ensure_ascii=False,indent=2)
draft['artifacts'].append(reference(p,'evidence/events/support90-v1.json','EVENT_SUPPORT90'))
# Correct only the current direct locator; prior published revisions stay untouched.
for c in draft['claims']:
    if c['id']=='C005':
        for r in c['evidence']:
            if r['artifact_id']=='S002v1_extract':r['locator']="'Экономика'!C3:I3"
candidate,changed=apply_event(p,draft,event)
assert changed
report=candidate['decision']['reviews'][-1]['impact']
assert len(report['comparison']['changes'])==1
assert report['comparison']['changes'][0]['locator']=="'Экономика'!E3"
assert any(x['artifact_id']=='FUNNEL1' for x in report['reusable'])
with (p/'evidence/correction-impact-v1.json').open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
candidate['artifacts'].append(reference(p,'evidence/correction-impact-v1.json','IMPACT1'))
with (p/'drafts/correction-event-v4.json').open('x',encoding='utf-8') as f:json.dump(candidate,f,ensure_ascii=False,indent=2)
saved=save_state(p,candidate)
print(json.dumps({'revision':saved['revision'],'changed_selected_cells':1,'funnel_reused':True,
                  'affected':[x['node'] for x in report['affected']],'review_status':'needs_review'}))
