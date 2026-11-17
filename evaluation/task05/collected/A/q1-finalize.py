import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path('scripts').resolve()))
import project_state as ps
import decision_followup as df

ROOT = Path.cwd()
P = ROOT.as_posix()
F = P + '/branches/familiar/projects/task04-followup'
V = P + '/branches/variant/projects/task04-followup'
verification = {}
for branch in ('familiar', 'variant'):
    project = Path('branches') / branch / 'projects/task04-followup'
    current = ps.load_state(project)
    previous = json.loads((project / 'state/previous.json').read_text(encoding='utf-8'))
    ps.validate_state(project, previous, require_saved=True)
    baseline = json.loads((Path('logs') / ('q1-' + branch + '-load') / 'stdout.txt').read_text(encoding='utf-8'))['state']
    assert previous == baseline
    assert current['revision'] == 3 and previous['revision'] == 2
    assert current['decision']['history'] == baseline['decision']['history']
    assert current['claims'] == baseline['claims']
    assert current['decision']['metrics'] == baseline['decision']['metrics']
    assert current['decision']['reviews'] == []
    assert all(next(a for a in current['artifacts'] if a['id'] == old['id']) == old for old in baseline['artifacts'])
    reconciled = df.reconcile(project, 'Q1-K-PROTOCOL-COMPLETE')
    assert reconciled['outcome'] == 'published'
    view = df.followup_view(current, '2026-12-19T12:00:00+03:00', '+03:00', 'simulated')
    commitments = {c['id']: c for c in view['commitments']}
    assert commitments['K-PROTOCOL']['status'] == 'completed'
    assert commitments['K-CAPABILITY']['attention'] == ['overdue']
    assert all(commitments[c]['attention'] == ['unassigned', 'blocked'] for c in ('K-BUDGET', 'K-VALUE'))
    verification[branch] = {
        'revision': current['revision'], 'state_sha256': current['state_sha256'],
        'previous_revision': previous['revision'], 'previous_state_sha256': previous['state_sha256'],
        'reconcile': reconciled, 'old_artifacts_preserved': True, 'history_unchanged': True,
        'claims_and_metrics_unchanged': True, 'reviews': [],
    }
    action = {
        'at': datetime.now(timezone.utc).isoformat(),
        'action': 'Q1 publication verified by separate load and reconcile',
        'outcome': 'published', 'revision': current['revision'],
        'state_sha256': current['state_sha256'], 'previous_preserved': True,
        'event_id': 'Q1-K-PROTOCOL-COMPLETE', 'errors': [],
    }
    with (project / 'state/actions.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(action, ensure_ascii=False) + '\n')

response = f'''Проектные правила Megafon присутствуют. На **19.12.2026, 12:00 (+03:00), по симулированным часам**, вывод для `familiar` и `variant` одинаков: приоритет — приёмка возможностей и решение о дальнейшей подготовке. Фактических результатов эксперимента нет.

| Обязательство | Состояние |
|---|---|
| `K-CAPABILITY` | Протокол приёмки не получен. Срок 17.11.2026, 12:00 пропущен на **32 суток**. Блокирует бюджет и внешние обещания. |
| `K-BUDGET` | Заблокировано приёмкой; ответственный и дата неизвестны. Просрочку установить нельзя. |
| `K-VALUE` | Заблокировано бюджетом; ответственный и дата неизвестны. Наблюдения ценности, частоты, продлений и расходов не получены. |
| `K-PROTOCOL` | На входе тоже было просрочено. В этом вызове локальный протокол подготовлен, проверен и завершение опубликовано. Это завершение документа, а не приёмки или пилота. |

Основания: `decision.commitments` в сохранённых revision 3 — [familiar]({F}/state/history/r000003.json), [variant]({V}/state/history/r000003.json); [расчёт сроков]({F}/notes/q1/chronology-v1.json), `deadline_elapsed_days`; [протокол]({F}/notes/q1/local-protocol-v1.md), пункты 1–5.

**Плановое окно `M-TIME` закончилось 18 декабря, сутки назад.** Старт и включение организаций не сообщались: завершённого эксперимента, успеха или провала из этого не следует. У `M-FIRST-PAY` и метрик масштабирования фактические окна и результаты неизвестны. Также наступила дата `G-FRESHNESS` — 1 декабря: перед следующим сравнением нужно проверить актуальность снимков S003/S004; сама дата их не опровергает. Локаторы: `decision.metrics[M-TIME].window`, остальные `metrics[].window`, `decision.conditions[G-FRESHNESS]` в указанных revision 3.

**Повтор коррекции не требует пересчёта или нового выбора.** Входящее сообщение прямо повторяет S005@1 без новой XLSX и измерений; 90 минут уже записаны в S002@2, `'Экономика'!E3`, и учтены в C014/C013 и ECON-v2. Прежние расчёты и outputs/v2 сохранены. Основания: [сообщение v1]({P}/inbox/q1/repeated-correction-v1.txt), строки 1–3; [S005@1]({F}/evidence/sources/S005/v1/original.txt), строки 1–5; [S002@2]({F}/evidence/sources/S002/v2/extract.json), указанная ячейка.

**Вернуться к владельцу нужно из-за отсутствия необходимых наблюдений и невыполненных предпосылок.** Следующий практический шаг — получить от технической роли протокол конкретной версии: доступ, скачивание, истечение и отзыв на разрешённом файле. Затем назначить ответственного за бюджет и отдельно решить, продолжать ли подготовку, с какими пределами затрат и новым календарём. Это рекомендация; новых дат и решений я не утверждал. Основание: [OWNER-INSTRUCTION v1]({F}/inputs/owner-instruction-v1.md), абзацы об обязательствах и возврате к решению. Исторический выбор остаётся `simulated_accepted` только для подготовки; реального разрешения запуска нет.

Ограничение утилиты: `impact` даже для `nonmaterial` повторно обходит совпадающие ссылки. Этот диагностический сигнал сохранён, но повтор не применён как новое изменение оснований; новых review не создано. [Разбор]({F}/notes/q1/review-and-reuse-v1.md), `Q1-TOOL`. Код утилит не менялся.

Передача контекста сохранена для [familiar]({F}/notes/q1/handoff-v1.md) и [variant]({V}/notes/q1/handoff-v1.md). Обе revision 3 повторно загружены и проверены; предыдущие версии сохранены. Полный первый ответ — [q1.md]({P}/responses/q1.md), метаданные запуска — [q1-meta.json]({P}/responses/q1-meta.json).
'''

responses = Path('responses')
responses.mkdir(exist_ok=True)
with (responses / 'q1.md').open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(response)
assert (responses / 'q1.md').read_text(encoding='utf-8') == response

logs = []
for record_path in sorted(Path('logs').glob('q1-*/result.json')):
    value = json.loads(record_path.read_text(encoding='utf-8'))
    logs.append({'label': record_path.parent.name, **value})
first_start = min(row['started_at'] for row in logs)
ended = datetime.now(timezone.utc).isoformat()
meta = {
    'request': 'q1', 'participant': 'A', 'workspace': str(ROOT),
    'started_at_utc': first_start, 'ended_at_utc': ended,
    'time_scope': 'Начало — первый инструментированный capture, после bootstrap. Конец — запись метаданных перед выводом итогового ответа. Это измеренный интервал, не точное время всего reasoning или активной работы.',
    'bootstrap_started_at_utc': None,
    'bootstrap_time_note': 'Первый разрешённый bootstrap не имел сохранённого UTC timestamp; время не восстанавливалось предположением.',
    'observed_interval_seconds': (datetime.fromisoformat(ended) - datetime.fromisoformat(first_start)).total_seconds(),
    'simulated_as_of': '2026-12-19T12:00:00+03:00',
    'megafon_project_rules_present': True,
    'model': None, 'tokens': None, 'charges': None, 'human_minutes': None,
    'unknown_resources_note': 'Точная модель, счётчики токенов, стоимость и время человека этому участнику не предоставлены; settings не менялись.',
    'errors_and_repeats': [
        {'kind': 'bootstrap_encoding', 'detail': 'Первое Get-Content без -Encoding UTF8 показало mojibake. request-q1.txt и RUNTIME.md перечитаны с UTF8 через q1-bootstrap-read-utf8.'},
        {'kind': 'display_truncation', 'detail': 'Часть больших tool outputs усечена в контексте; полные stdout/stderr сохранены capture. Решающее содержание перечитано целевыми фрагментами; публикации не повторялись.'},
        {'kind': 'input_duplicate', 'detail': 'Входящий повтор S005@1 не применялся как новое изменение. Повторный импорт S002/S005 и пересчёт прежних outputs не выполнялись; зарегистрирована только новая квитанция Q1-REPEAT@1.'},
        {'kind': 'utility_limitation', 'detail': 'Штатный nonmaterial impact обходит совпадающие ссылки и возвращает 16 узлов в каждой ветке. Диагностика сохранена, новое evidence_change не применено; реализации не менялись.'},
    ],
    'external_help': [
        {'kind': 'parent_coordinator_task_relay', 'detail': 'Переданы выделенная папка и требование исполнить request-q1.txt/RUNTIME.md; содержательных подсказок по решению не было.'},
        {'kind': 'infrastructure_message', 'detail': 'Родитель одинаково для участников уточнил: при отказе прав не обходить ограничение; при невозможности записи вернуть полный ответ и ошибку. Отказов прав здесь не было, сохранение удалось; содержательных подсказок не было.'},
    ],
    'subagents_spawned': 0, 'live_web_used': False, 'other_external_services_used': [],
    'reads_outside_capture': [
        {'paths': ['request-q1.txt', 'RUNTIME.md'], 'reason': 'Разрешённый bootstrap через Get-Content; UTF8 затем перечитан через capture.'},
    ],
    'writes_outside_capture': [
        {'tool': 'apply_patch', 'path': 'q1-inspect.py', 'reason': 'Новый механический помощник чтения и сравнения.'},
        {'tool': 'apply_patch', 'path': 'q1-prepare.py', 'reason': 'Новый механический помощник записи подготовленных координатором артефактов и проверки draft штатными API.'},
        {'tool': 'apply_patch', 'path': 'q1-finalize.py', 'reason': 'Новый механический помощник финальной проверки и сохранения ответа/метаданных.'},
    ],
    'shell_workdir_explicit_in_every_call': True,
    'capture': {
        'completed_records_before_this_command': len(logs),
        'sum_completed_subprocess_elapsed_seconds': sum(row['elapsed_seconds'] for row in logs),
        'failed_completed_commands': [row['label'] for row in logs if row['returncode'] != 0],
        'records': logs,
        'current_finalization_label': 'q1-finalize',
        'finalization_note': 'stdout/stderr/result текущей команды сохранятся в logs/q1-finalize после её завершения; её elapsed ещё не включён в сумму выше.',
    },
    'verification': verification,
    'answer': {'path': 'responses/q1.md', 'sha256': hashlib.sha256((responses / 'q1.md').read_bytes()).hexdigest(), 'immutable_first_final_response': True},
    'handoffs': ['branches/familiar/projects/task04-followup/notes/q1/handoff-v1.md', 'branches/variant/projects/task04-followup/notes/q1/handoff-v1.md'],
    'state_writers': 1, 'business_choice_added': False, 'real_world_actions_performed': False,
}
with (responses / 'q1-meta.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(meta, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
assert json.loads((responses / 'q1-meta.json').read_text(encoding='utf-8'))['answer']['sha256'] == meta['answer']['sha256']
print(json.dumps({'saved_answer': 'responses/q1.md', 'answer_sha256': meta['answer']['sha256'], 'meta': 'responses/q1-meta.json', 'verification': verification, 'ended_at_utc': ended}, ensure_ascii=False, indent=2))
print(response)
