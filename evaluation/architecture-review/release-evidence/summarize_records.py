"""Summarize only measured records; do not rerun historical processes."""
import json
import hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent

def readj(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

record={'scope':'Сверка сохранённых измерений, без новых вызовов LLM и без повторного запуска старых тестов',
        'model_configured':'gpt-6-astra', 'effective_server_model':None,
        'actual_charges':None,'api_equivalent_estimate':None,'human_active_time':None,
        'cost_limit':'Точный серверный вариант и применимая ставка API не установлены; счётчики подписочной сессии не равны списаниям. Цена не выдумывается.',
        'known_usage':[], 'intervals':[], 'baseline_processes':[],
        'accounting_rule':'Для каждого thread берётся последняя наблюдаемая total; cached вложен во input, reasoning вложен в output. Разные этапы одного thread повторно не суммируются. Временные интервалы частично перекрываются; общего времени разработки здесь нет.'}

cli=ROOT/'evaluation/task07/observations/continuation-cli'
events=[json.loads(line) for line in (cli/'stdout.txt').read_text(encoding='utf-8').splitlines() if line.strip()]
for i,e in enumerate(events,1):
    if e.get('type')=='turn.completed':
        record['known_usage'].append({'thread':events[0]['thread_id'],'scope':'Только завершённое первое продолжение; поздний synthesis не дал итогового usage',
            'source':'evaluation/task07/observations/continuation-cli/stdout.txt','line':i,'usage':e['usage']})
for name in ['q2-A-02','q2-B-02']:
    p=ROOT/'evaluation/task07/comparison'/name/'result.json'; d=readj(p)
    record['known_usage'].append({'thread':d['thread_id'],'scope':'Последний наблюдаемый накопительный счётчик неполного сравнения',
        'source':p.relative_to(ROOT).as_posix(),'json_pointer':'/token_usage/tokenUsage/total','usage':d['token_usage']['tokenUsage']['total']})
for rel in ['evaluation/task07/observations/continuation-cli/result.json','evaluation/task07/observations/synthesis-cli/result.json',
            'evaluation/task07/comparison/q1-A-01/result.json','evaluation/task07/comparison/q1-B-01/result.json',
            'evaluation/task07/comparison/q2-A-02/result.json','evaluation/task07/comparison/q2-B-02/result.json']:
    p=ROOT/rel; d=readj(p)
    record['intervals'].append({'source':rel,**{k:d.get(k) for k in ['started_at','ended_at','elapsed_seconds','outcome','returncode']}})

for name in ['setup-create','setup-install','setup-pip-check','regression','release-check']:
    p=ROOT/'dist/Материалы-2026-11-16/Проверки'/name/'result.json';d=readj(p)
    record['baseline_processes'].append({'source':p.relative_to(ROOT).as_posix(),
        **{k:d.get(k) for k in ['argv','returncode','started_at','ended_at','elapsed_seconds']},
        'stdout_hash_ok':sha(p.parent/'stdout.txt')==d.get('stdout_sha256'),
        'stderr_hash_ok':sha(p.parent/'stderr.txt')==d.get('stderr_sha256')})

with (OUT/'measured-resources.json').open('x',encoding='utf-8') as f:
    json.dump(record,f,ensure_ascii=False,indent=2)
print(json.dumps(record,ensure_ascii=False,indent=2))
