"""Снять фактические границы TASK04 без выдуманных token/cost estimates."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
start = datetime.fromisoformat('2026-11-16T11:36:25+00:00')
end = datetime.now(timezone.utc)
demo_start = json.loads((BASE / 'observations/demo-prepare/result.json').read_text(encoding='utf-8'))['started_at']
demo_end = json.loads((BASE / 'acceptance.json').read_text(encoding='utf-8'))['observed_at']
commands = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((BASE / 'observations').glob('*/result.json'))]
def duration(a, b):
    return (datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds()
value = {'recorded_at': end.isoformat(), 'timezone_for_display': 'Europe/Moscow (+03:00)',
         'development': {'started_at': start.isoformat(), 'ended_at': end.isoformat(), 'elapsed_seconds': (end - start).total_seconds(),
                         'scope': 'Gross wall interval: реализация, demo, review, тесты, документация; не активное время человека'},
         'demo': {'started_at': demo_start, 'ended_at': demo_end, 'elapsed_seconds': duration(demo_start, demo_end),
                  'scope': 'Подготовка изолированной копии → текущий host lifecycle → отдельная локальная приёмка r11'},
         'interval_rule': 'Demo, команды, reviewer и ожидания вложены в development; интервалы не складывать.',
         'recorded_command_runs': len(commands), 'recorded_nonzero_command_runs': sum(c['returncode'] != 0 for c in commands),
         'command_elapsed_seconds_not_additive': [{'command': c['command'], 'started_at': c['started_at'], 'ended_at': c['ended_at'],
                                                  'elapsed_seconds': c['elapsed_seconds'], 'returncode': c['returncode']} for c in commands],
         'retries_and_fixes': [
             'Один reviewer использован несколькими проходами; находки и actual test runs в independent-review-v2.md.',
             'Reviewer наблюдал один unit failure ожидания текста ошибки; boundary уже отклонял опасное действие. Исправлен regex, затронутые checks повторены.',
             'Два полных финальных regression runs: 80 затем 81 после дополнительного guard новых legacy approvals. Это развитие тестов, не quota.',
             'Два сохранённых recovery harness runs: первый до уточнения publication_unknown; финальный после. Старые результаты не переписаны.',
             'Один apply_patch отвергнут: Delete+Add одного DEVELOPMENT_STATE в одном patch. Файл не изменился; затем применён обычный Update с сохранённым history.',
             'Один короткий диагностический python -c показал mojibake stdout из legacy Windows encoding; source bytes не менялись. CLI явно UTF-8, далее -X utf8.',
             'Эквивалентных nested fresh Codex launches: не выполнялись. Auth/provider/restrictions не менялись.'
         ],
         'human_assistance': {'observed': 'Исходный TASK04 авторизовал локальную разработку/симуляцию; последующих сообщений или бизнес-решения в ходе выполнения не получено.',
                              'active_minutes': None, 'reason': 'Телеметрия активной работы человека недоступна'},
         'models': {'coordinator': 'Существующий Codex host', 'independent_review_agents': 1, 'exact_model_id': None, 'tokens': None},
         'cost': {'charges': None, 'currency': None, 'basis': 'unknown', 'note': 'Телеметрии тарификации нет; отсутствие новых провайдеров не означает нулевой стоимости'},
         'new_dependencies_or_providers': [], 'business_experiment_executed': False,
         'research_used': ['https://docs.python.org/3.12/library/os.html#os.replace'],
         'final_code_sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                              [ROOT / 'scripts/project_state.py', ROOT / 'scripts/decision_followup.py', ROOT / 'tests/test_followup.py', ROOT / 'tests/test_followup_recovery.py']}}
with (BASE / 'resource-accounting.json').open('x', encoding='utf-8') as stream:
    json.dump(value, stream, ensure_ascii=False, indent=2)
sys.stdout.reconfigure(encoding='utf-8')
print(json.dumps({k: value[k] for k in ('development', 'demo', 'recorded_command_runs', 'cost')}, ensure_ascii=False, indent=2))
