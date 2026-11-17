"""Наблюдаемые интервалы, без токенных оценок и суммирования пересечений."""
from pathlib import Path
from datetime import datetime, timezone
import json

BASE=Path(__file__).resolve().parent


def stamp(value):
    return datetime.fromisoformat(value.replace('Z','+00:00'))


def union_seconds(intervals):
    merged=[]
    for start,end in sorted(intervals):
        if not merged or start>merged[-1][1]:
            merged.append([start,end])
        else:
            merged[-1][1]=max(merged[-1][1],end)
    return sum((end-start).total_seconds() for start,end in merged)


def main():
    results={'scope':'Интервалы от первого до последнего captured subprocess каждого шага; bootstrap и доставка final могут быть вне них. Это наблюдаемый wall interval с reasoning gaps, не активное время человека/модели.',
             'participants':{},'model_id':None,'model_settings_exact':None,'tokens':None,'charges':None,'human_active_time':None,
             'ordinary_B':'NOT_RUN','subagent_route':'fork_turns=none; no explicit model/settings override; inherited AGENTS',
             'assistance':'Одно одинаковое техническое сообщение обоим в q1; содержательных подсказок и assisted answer revisions нет',
             'observed_at':datetime.now(timezone.utc).isoformat()}
    all_intervals=[]
    for condition in ('A','B'):
        condition_intervals=[]
        phase_results={}
        for phase in ('q1','q2','q3'):
            paths=sorted((BASE/'collected'/condition/'logs').glob(phase+'*/result.json'))
            logs=[json.loads(p.read_text(encoding='utf-8')) for p in paths]
            intervals=[(stamp(x['started_at']),stamp(x['ended_at'])) for x in logs]
            start=min(x[0] for x in intervals)
            end=max(x[1] for x in intervals)
            condition_intervals.append((start,end))
            all_intervals.append((start,end))
            phase_results[phase]={'started_at':start.isoformat(),'ended_at':end.isoformat(),
                'elapsed_seconds':(end-start).total_seconds(),'captured_commands':len(logs),
                'nonzero_returncodes':[{'path':str(p.relative_to(BASE)), 'returncode':x['returncode']} for p,x in zip(paths,logs) if x['returncode']],
                'command_interval_union_seconds':union_seconds(intervals),
                'all_cwd_in_assigned_workspace':all(Path(x['cwd']).resolve()==Path('C:/Users/BastaPC/AppData/Local/Temp/megafon-task05-clean-20zjuuxd')/condition for x in logs)}
        results['participants'][condition]={'phases':phase_results,'nonoverlapping_execution_seconds':union_seconds(condition_intervals),
            'between_phase_waiting_excluded':True,'captured_commands':sum(x['captured_commands'] for x in phase_results.values())}
    results['paired_execution_wall_union_seconds']=union_seconds(all_intervals)
    frozen=json.loads((BASE/'freeze-manifest-v2.json').read_text(encoding='utf-8'))
    results['preparation']={'start':'2026-11-16T13:23:55+00:00','end':frozen['frozen_at'],
        'elapsed_seconds':(stamp(frozen['frozen_at'])-stamp('2026-11-16T13:23:55+00:00')).total_seconds(),
        'includes':'чтение TASK04, host probe, протокол/критерии/новые события, фильтрация/нормализация пакетов; не только CPU копирования',
        'prior_state_creation':'TASK04 r3 — прежняя разработка. Труд только создания r3 неизвестен и не распределялся на запрос. Это не бесплатная подготовка.',
        'neutral_package_cpu_observations':['prepare-observation.json','prepare-v2-observation.json','observations/prepare-02','observations/prepare-v2'],
        'preparation_failure':'preparation-failure-01.json; v1 исключён из measured runs до запуска'}
    begin=json.loads((BASE/'observations/controls-before/result.json').read_text(encoding='utf-8'))
    end=json.loads((BASE/'observations/regression-final-03/result.json').read_text(encoding='utf-8'))
    results['fixes_and_checks_window']={'start':begin['started_at'],'end':end['ended_at'],
        'elapsed_seconds':(stamp(end['ended_at'])-stamp(begin['started_at'])).total_seconds(),
        'note':'Охватывает controls, кодовые проверки и исправления с паузами; пересекается с участниками, не складывать с их временем. Не активное время инженера.'}
    results['grading']={'start_observed':'2026-11-16T14:12:48+00:00','meta':'review-input/review-meta.json',
        'note':'Отдельное автоматическое review; итоговый интервал указан в meta. Подготовка его пакета включает build_review.py и acceptance-01.'}
    with (BASE/'resource-accounting.json').open('x',encoding='utf-8') as f:
        json.dump(results,f,ensure_ascii=False,indent=2)
    print(json.dumps(results,ensure_ascii=False,indent=2))


if __name__=='__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    main()
