"""Source arithmetic, hashes, state invariants; без оценки прозы по ключевым словам."""
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
import argparse
import hashlib
import json
import sys
from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parents[2]
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
import project_state as ps


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True)
    parser.add_argument('--runs',default='evaluation/task05/collected')
    args=parser.parse_args()
    results={'at':datetime.now(timezone.utc).isoformat()}
    frozen=read(BASE/'freeze-manifest-v2.json')
    results['freeze']={'files':len(frozen['files']), 'mismatches':[p for p,h in frozen['files'].items() if sha(BASE/p)!=h]}
    protection=read(BASE/'protection-before.json')
    results['protected']={}
    for folder, files in protection.items():
        mismatch=[p for p,h in files.items() if not (ROOT/folder/p).is_file() or sha(ROOT/folder/p)!=h]
        actual={p.relative_to(ROOT/folder).as_posix() for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        results['protected'][folder]={'files':len(files),'mismatches':mismatch,'added':sorted(actual-set(files))}
    results['historical_reports']={p:sha(ROOT/p)==h for p,h in read(BASE/'historical-docs-before.json').items()}
    results['canonical']={}
    for name in ('demo-001','demo-002'):
        state=ps.load_state(ROOT/'projects'/name)
        results['canonical'][name]={'revision':state['revision'],'decision_status':state['decision']['status']}
    a=BASE/'frozen-v2/A/branches/familiar/projects/task04-followup'
    b=BASE/'frozen-v2/B'
    original=ps.load_state(a)
    results['input_parity']={'same_readable_context':sha(BASE/'frozen-v2/A/context.md')==sha(b/'context.md'),
        'same_primary_artifacts':all(sha(a/x['path'])==sha(b/'materials'/x['path']) for x in original['artifacts']),
        'artifact_count':len(original['artifacts'])}
    book=load_workbook(a/'evidence/sources/S002/v2/original.xlsx',read_only=True,data_only=False)
    sheet=book['Экономика']
    values={f'{col}3':Decimal(str(sheet[f'{col}3'].value)) for col in 'CDEFGHI'}
    contribution=values['C3']-values['D3']-values['E3']*values['F3']/60
    remainder=values['I3']*contribution-values['G3']
    funnel=book['Воронка']
    paid_trial=[Decimal(str(funnel[f'F{row}'].value))/Decimal(str(funnel[f'D{row}'].value))*100 for row in (3,4)]
    book.close()
    results['source_calculation']={'source':'S002@2 original.xlsx; Экономика!C3:I3; Воронка!D3:F4',
        'values':{k:str(v) for k,v in values.items()},'contribution':str(contribution),'remainder_N20':str(remainder),
        'paid_trial_pct':[str(x) for x in paid_trial], 'synthetic_scenario':True}
    now=datetime.fromisoformat('2026-12-19T12:00:00+03:00')
    results['dates']={name:(now-datetime.fromisoformat(date)).total_seconds()/86400 for name,date in {
        'deadline_days':'2026-11-17T12:00:00+03:00','planned_window_days':'2026-12-18T12:00:00+03:00',
        'freshness_days':'2026-12-01T12:00:00+03:00'}.items()}
    results['participant_A']={}
    runs=ROOT/args.runs
    for branch in ('familiar','variant'):
        project=runs/'A/branches'/branch/'projects/task04-followup'
        current=ps.load_state(project)
        start=ps.load_state(BASE/'frozen-v2/A/branches'/branch/'projects/task04-followup')
        q2=read(BASE/'runs/A/q2'/(branch+'-state.json'))
        results['participant_A'][branch]={'revision':current['revision'],'history_unchanged':current['decision']['history']==start['decision']['history'],
            'commitment_ids_unchanged':[x['id'] for x in current['decision']['commitments']]==[x['id'] for x in start['decision']['commitments']],
            'source_artifacts_unchanged':all(sha(project/x['path'])==x['sha256'] for x in start['artifacts']),
            'q2_reviews_retained_in_q3':current['decision']['reviews']==q2['decision']['reviews'],
            'q2_outputs_retained_in_q3':current['decision'].get('current_outputs')==q2['decision'].get('current_outputs'),
            'open_owner_reviews':[x['id'] for x in current['decision']['reviews'] if x['owner_review_required']],
            'status':current['decision']['status']}
    results['responses']={}
    for condition,name in [('A','A'),('B-ablation','B')]:
        initial_map=read(BASE/'runs'/condition/'q1/manifest.json')['files']
        for phase in ('q1','q2','q3'):
            snap=BASE/'runs'/condition/phase/(phase+'.md')
            final=runs/name/'responses'/(phase+'.md')
            results['responses'][condition+'/'+phase]={'sha256':sha(snap),'same_as_final':sha(snap)==sha(final)}
    results['participant_B']={'initial_materials_unchanged':all(sha(runs/'B'/p)==h for p,h in read(BASE/'runs/B-ablation/q1/manifest.json')['files'].items()
            if p.startswith('materials/')),
        'notes_exist':{branch:sorted(p.relative_to(runs/'B').as_posix() for p in (runs/'B/notes'/branch).glob('*')) for branch in ('familiar','variant')},
        'private_schema_required':False,'semantic_persistence':'оценивается по полным notes/ответам отдельно, не по filenames A'}
    assert not results['freeze']['mismatches']
    assert all(not x['mismatches'] and not x['added'] for x in results['protected'].values())
    assert all(results['historical_reports'].values())
    assert all(x['decision_status']=='awaiting_decision' for x in results['canonical'].values())
    assert contribution==1500 and remainder==0 and paid_trial==[25,10]
    assert all(results['input_parity'][k] for k in ('same_readable_context','same_primary_artifacts'))
    assert all(x['same_as_final'] for x in results['responses'].values())
    for checks in results['participant_A'].values():
        assert all(checks[k] for k in ('history_unchanged','commitment_ids_unchanged','source_artifacts_unchanged','q2_reviews_retained_in_q3','q2_outputs_retained_in_q3'))
    with Path(args.output).open('x',encoding='utf-8') as f:
        json.dump(results,f,ensure_ascii=False,indent=2)
    print(json.dumps({'ok':True,'canonical':results['canonical'],'participant_A':results['participant_A']},ensure_ascii=False))


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
