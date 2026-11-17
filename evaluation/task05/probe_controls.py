"""Два предметных контроля на изолированной копии; не LLM benchmark."""
from pathlib import Path
import argparse
import copy
from datetime import datetime, timezone
import json
import shutil
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--code-root', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    base = Path(__file__).resolve().parent
    sys.path.insert(0, str(Path(args.code_root).resolve()/'scripts'))
    import project_state as ps
    import decision_followup as df
    original = base/'frozen-v2/A/branches/familiar/projects/task04-followup'
    with tempfile.TemporaryDirectory(prefix='task05-controls-') as tmp:
        project = Path(tmp)/'task04-followup'
        shutil.copytree(original, project)
        data = ps.load_state(project)
        for aid, name in [('REPEAT-INPUT','q1/repeated-correction-v1.txt'),('WITHDRAW-INPUT','q2/familiar-withdrawal-v1.txt')]:
            dest = project/'inputs'/Path(name).name
            shutil.copyfile(base/'frozen-v2/events'/name,dest)
            data['artifacts'].append(ps.reference(project, str(dest.relative_to(project)), aid))
        data = ps.save_state(project,data)
        def event(eid, kind, aid):
            return dict(id=eid,project_id=data['project_id'],kind='evidence_change',at='2026-12-19T12:00:00+03:00',
                provenance=dict(kind='source_material',artifact_id=aid,locator='line:1-4'),change=kind)
        repeat = event('CONTROL-REPEAT',dict(type='corrected_value',source={'id':'S002','version':1},
            replacement={'id':'S002','version':2},locators=["'Экономика'!E3"],reason='Повтор уже включённой коррекции',
            old_ground='30 минут',new_ground='90 минут',applicability='Тот же сценарий и те же закреплённые версии'), 'REPEAT-INPUT')
        withdrawal = event('CONTROL-WITHDRAW',dict(type='withdrawn_support',source={'id':'S001','version':1},
            locators=['physical-page:1/block:5'],reason='Автор отозвал поддержку отсутствия аккаунта',
            old_ground='recipient needs no account',new_ground='поддержка отозвана, нового испытания нет',
            applicability='Тот же прототип'),'WITHDRAW-INPUT')
        view = df.followup_view(data,'2026-12-19T12:00:00+03:00','+03:00','simulated')
        candidate, changed = df.apply_event(project,data,repeat)
        report = candidate['decision']['reviews'][-1]
        with_review, _ = df.apply_event(project,data,withdrawal)
        after_repeat, _ = df.apply_event(project,with_review,repeat)
        result = {'at':datetime.now(timezone.utc).isoformat(),'code_root':str(Path(args.code_root).resolve()),
            'source':'frozen-v2 native r2; новая disposable r3 регистрирует контрольные inputs',
            'planned_unstarted_window':next(m for m in view['metrics'] if m['id']=='M-TIME'),
            'repeat_without_independent_review':{'changed':changed,'owner_review_required':report['owner_review_required'],
                'status':report['status'],'impact':report['impact']},
            'repeat_with_legitimate_review':[{'id':r['id'],'owner_review_required':r['owner_review_required'],'status':r['status']}
                for r in after_repeat['decision']['reviews']],
            'invariants':{'history_unchanged':after_repeat['decision']['history']==data['decision']['history'],
                          'commitments_unchanged':after_repeat['decision']['commitments']==data['decision']['commitments']}}
    out=Path(args.output)
    with out.open('x',encoding='utf-8') as f:
        json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({'window':result['planned_unstarted_window']['window_state'],
        'repeat_owner_review':report['owner_review_required'],'with_legitimate_review':result['repeat_with_legitimate_review'],
        'invariants':result['invariants']},ensure_ascii=False))


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
