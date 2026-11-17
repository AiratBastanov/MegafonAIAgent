"""Temporary mechanical driver. Content is authored in explicit project files by Codex."""
from pathlib import Path
import copy, json, sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
WS = ROOT / 'evaluation/task07/demo-workspace'
P = WS / 'projects/task06-rehearsal'
sys.path.insert(0, str(WS / 'scripts'))
from project_state import load_state, save_state, validate_state, reference
from decision_followup import apply_event, impact, followup_view

def read(path):
    return json.loads((P/path).read_text(encoding='utf-8'))

def write(path, data):
    dest=P/path
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(data,f,ensure_ascii=False,indent=2); f.write('\n')

def add(data, aid, path):
    assert aid not in {a['id'] for a in data['artifacts']}
    data['artifacts'].append(reference(P,path,aid))

def publish(data, path):
    validate_state(P,data)
    write(path,data)
    saved=save_state(P,data)
    loaded=load_state(P)
    assert saved==loaded
    print('Сохранена новая версия; отдельное чтение и хеши проверены.')
    print('Предыдущая версия и исходные файлы сохранены.')
    print('Время сохранения:',loaded['saved_at'])
    return loaded

def seal():
    old=load_state(P); assert old['revision']==5
    d=read('drafts/checkpoint-v6-synthesis.json')
    for aid,path in [('OPTIONS_V3','outputs/v3/options.md'),('VALIDATION_V3','outputs/v3/validation-plan.md'),
                     ('EDITORIAL_REVIEW','inputs/editorial-review-v1.md'),('COORDINATOR_REVIEW','evidence/coordinator-review-v1.md')]:
        add(d,aid,path)
    mapping={'OPTIONS_V2':'OPTIONS_V3','VALIDATION_V2':'VALIDATION_V3'}
    d['decision']['current_outputs'].update({'options':'OPTIONS_V3','validation-plan':'VALIDATION_V3'})
    for condition in d['decision']['conditions']:
        condition['output_ids']=[mapping.get(a,a) for a in condition['output_ids']]
    c=next(c for c in d['claims'] if c['id']=='C024')
    c['text']=c['text'].replace('или повторных платежей','или первых/повторных платежей')
    for e in c['evidence']: e['artifact_id']=mapping.get(e['artifact_id'],e['artifact_id'])
    d['decision']['proposed_option']=d['decision']['proposed_option'].replace('или повторной оплаты','или первых/повторных оплат')
    d['completed'].append('Координатор проверил подготовленный кандидат после сервисного лимита; исправил ER03 в двух новых документах, остальные три и расчёты переиспользованы.')
    d['next_action']='Рассмотреть сохранённые варианты и совместные пороги проверки; бизнес-действия требуют отдельного решения.'
    d['coordinator_completion']={'origin':'current_coordinator_after_cli_usage_limit','review':'COORDINATOR_REVIEW','unfinished_draft_preserved':'drafts/checkpoint-v6-synthesis.json'}
    publish(d,'drafts/coordinator-synthesis-v1.json')
    print('Пять документов готовы. Исправлено условие первых оплат.')
    print('Три документа и все исходные расчёты использованы без изменений.')
    print('Выбор ожидает руководителя. Реального пилота и продаж нет.')

def event(content_path):
    spec=read(content_path); d=copy.deepcopy(load_state(P))
    for aid,path in spec.get('new_artifacts',{}).items(): add(d,aid,path)
    d.update(spec.get('state_updates',{}))
    d['decision'].update(spec.get('decision_updates',{}))
    d['decision']['metrics']+=spec.get('metrics_additions',[])
    for condition in d['decision']['conditions']:
        if condition['id'] in spec.get('condition_updates',{}):condition.update(spec['condition_updates'][condition['id']])
    d['claims']+=spec.get('new_claims',[])
    if spec.get('restore_claims'):
        original=read('state/history/r%06d.json'%spec['restore_claims']['revision'])
        old_claims={c['id']:c for c in original['claims']}
        d['claims']=[copy.deepcopy(old_claims[c['id']]) if c['id'] in spec['restore_claims']['ids'] else c for c in d['claims']]
    for item in d['decision']['commitments']:
        if item['id'] in spec.get('commitment_updates',{}):item.update(spec['commitment_updates'][item['id']])
    for condition in d['decision']['conditions']:
        condition['output_ids']=[spec.get('output_mapping',{}).get(a,a) for a in condition['output_ids']]
    d.setdefault('artifact_dependencies',[]).extend(spec.get('artifact_dependencies',[]))
    for c in d['claims']:
        if c['id'] in spec.get('claim_updates',{}):c.update(spec['claim_updates'][c['id']])
    for source in spec.get('register_sources',[]):
        sid,version=source['id'],source['version']
        meta=read(f'evidence/sources/{sid}/v{version}/source.json'); prefix=f'{sid}v{version}'
        ids=[]
        for kind,path in [('meta',f'evidence/sources/{sid}/v{version}/source.json'),('original',meta['original']['path']),('extract',meta['extract']['path'])]:
            aid=prefix+'_'+kind;add(d,aid,path);ids.append(aid)
        d['sources'].append({'id':sid,'version':version,'artifact_ids':ids,'synthetic':meta['synthetic']})
    e=spec['event'];e['at']=datetime.now(timezone.utc).isoformat();e['project_id']=d['project_id']
    write(spec['event_path'],e)
    if e['kind']=='evidence_change':
        report=impact(P,d,e);write(spec['impact_path'],report)
        print('Изменение проверено через связи источника, расчётов и решения.')
    d,changed=apply_event(P,d,e);assert changed
    publish(d,spec['draft_path'])
    for line in spec.get('display',[]):print(line)

def view():
    d=load_state(P); tz=timezone(__import__('datetime').timedelta(hours=3))
    v=followup_view(d,datetime.now(tz).isoformat(),'+03:00','actual')
    print('Учебный пример: выбор, роли и затраты смоделированы.\n')
    if v['history']:
        h=v['history'][-1]
        print('ИСТОРИЯ:',h['option'])
        print('При выборе: поддержка 30 минут в месяц.\n')
    print('СЕЙЧАС:',v['proposed_option'].replace('Поддержка90','Поддержка 90').replace('при20','при 20'),'\n')
    for c in v['commitments']:
        status={'pending':'ожидает выполнения','blocked':'заблокировано','completed':'выполнено','cancelled':'отменено'}[c['status']]
        owner=c['owner'].split(' (')[0]
        due=datetime.fromisoformat(c['due_at']).strftime('%d.%m, %H:%M МСК') if c['due_at'] else 'после зависимых проверок'
        print(owner+' — '+status+'; '+due)
    print('\nОбязательства не выполнены. Пилот не начат.')
    print('Решение руководителя требуется:', 'да' if any(r['owner_review_required'] for r in v['reviews']) else 'нового требования нет')

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if sys.argv[1]=='seal':seal()
    elif sys.argv[1]=='event':event(sys.argv[2])
    elif sys.argv[1]=='view':view()
