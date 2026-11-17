"""Seal the coordinator's explicit review through the existing event/state utilities."""
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from scripts.project_state import reference,save_state
from scripts.decision_followup import apply_event
p=Path('projects/task06-rehearsal')
d=json.loads((p/'drafts/final-v5.json').read_text(encoding='utf-8'))
event={'id':'EV_SUPPORT90_REVIEW','project_id':'task06-rehearsal','kind':'review',
       'at':datetime.now(timezone.utc).isoformat(),'provenance':{'kind':'agent_review','artifact_id':'REVIEW2','locator':'Последствия коррекции'},
       'review_id':'review-EV_SUPPORT90','resolution':{'status':'revised',
        'reason':'Новая база существенно снижает остаток до нуля при 20; старые расчёты не текущая поддержка',
        'next_action':'Владелец определяет допустимое исследование/бюджет либо keep/close; пилот не запущен',
        'resolution_evidence':[{'artifact_id':'REVIEW2','locator':'Затронутое/незатронутое'},{'artifact_id':'ECON2','locator':'base'}],
        'owner_review_required':True,'proposed_option':'Ограниченное исследование задачи и поддержки после решения владельца; коммерческий пилот не разрешён'}}
with (p/'evidence/events/support90-review-v1.json').open('x',encoding='utf-8') as f:json.dump(event,f,ensure_ascii=False,indent=2)
d['artifacts'].append(reference(p,'evidence/events/support90-review-v1.json','EVENT_REVIEW90'))
d,changed=apply_event(p,d,event);assert changed
for c in d['claims']:
    if c['id'] in ('C005','C007'):
        c['status']='superseded';c['support_reason']='Историческое основание v1 сохранено; текущие C008/C009 и REVIEW2'
d['decision']['current_outputs']={name:aid for name,aid in zip(
    ('situation','options','product-strategy','communication-strategy','validation-plan'),
    ('OUT2_SITUATION','OUT2_OPTIONS','OUT2_PRODUCT','OUT2_COMM','OUT2_VALIDATION'))}
d['decision']['conditions'][0].update(claim_ids=['C008','C009'],output_ids=list(d['decision']['current_outputs'].values()))
saved=save_state(p,d)
print(json.dumps({'revision':saved['revision'],'stage':saved['stage'],'decision':saved['decision']['status'],
    'owner_review_required':True,'accepted_choices':len(saved['decision']['history'])}))
