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
    initial_load = json.loads((Path('logs') / ('q2-' + branch + '-load') / 'stdout.txt').read_text(encoding='utf-8'))['state']
    assert previous == initial_load and previous['revision'] == 3 and current['revision'] == 4
    assert current['decision']['history'] == previous['decision']['history']
    assert current['decision']['status'] == 'simulated_accepted'
    assert current['decision']['events'][:len(previous['decision']['events'])] == previous['decision']['events']
    assert [e['kind'] for e in current['decision']['events'][len(previous['decision']['events']):]] == ['evidence_change', 'review']
    assert current['decision']['metrics'] == previous['decision']['metrics']
    assert all(next(a for a in current['artifacts'] if a['id'] == old['id']) == old for old in previous['artifacts'])
    assert current['sources'][:len(previous['sources'])] == previous['sources']
    assert len(current['decision']['reviews']) == 1
    review = current['decision']['reviews'][0]
    assert review['status'] == 'revised' and review['owner_review_required'] is True
    assert len(review['impact']['affected']) == 16
    assert all(item['node'] != 'artifact:Q2-RAW-IMPACT' for item in review['impact']['affected'])
    assert next(c for c in current['claims'] if c['id'] == 'C015')['status'] == 'withdrawn'
    for cid in ('C007', 'C008', 'C012', 'C013', 'C014'):
        assert next(c for c in current['claims'] if c['id'] == cid) == next(c for c in previous['claims'] if c['id'] == cid)
    assert next(c for c in current['decision']['commitments'] if c['id'] == 'K-PROTOCOL') == next(c for c in previous['decision']['commitments'] if c['id'] == 'K-PROTOCOL')
    statuses = {}
    for suffix in ('WITHDRAWAL', 'REVIEW'):
        event_id = 'Q2-' + branch.upper() + '-' + suffix
        reconciled = df.reconcile(project, event_id)
        assert reconciled['outcome'] == 'published'
        statuses[event_id] = reconciled
    view = df.followup_view(current, '2026-12-19T13:00:00+03:00', '+03:00', 'simulated')
    commitment_map = {c['id']: c for c in view['commitments']}
    assert commitment_map['K-CAPABILITY']['attention'] == ['overdue']
    assert all(commitment_map[c]['attention'] == ['unassigned', 'blocked'] for c in ('K-BUDGET', 'K-VALUE'))
    assert view['metrics'][0]['window_state'] == 'ended_evidence_required'
    baseline_note = json.loads((project / 'notes/q2/baseline-v1.json').read_text(encoding='utf-8'))
    for name, expected_hash in baseline_note['q1_response_hashes'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected_hash
    verification[branch] = {
        'revision': current['revision'], 'state_sha256': current['state_sha256'],
        'previous_revision': previous['revision'], 'previous_state_sha256': previous['state_sha256'],
        'reconcile': statuses, 'old_artifacts_and_sources_preserved': True, 'history_unchanged': True,
        'economic_claims_and_metrics_unchanged': True, 'q1_completion_unchanged': True,
        'review_status': review['status'], 'owner_review_required': True,
        'current_outputs': current['decision']['current_outputs'],
        'q1_response_hashes_unchanged': baseline_note['q1_response_hashes'],
    }
    with (project / 'state/actions.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps({
            'at': datetime.now(timezone.utc).isoformat(), 'action': 'Q2 publication verified',
            'outcome': 'separate_load_and_reconcile_passed', 'revision': 4,
            'state_sha256': current['state_sha256'], 'previous_preserved': True,
            'history_preserved': True, 'owner_review_required': True,
            'real_actions': False, 'new_choice': False,
        }, ensure_ascii=False) + '\n')

response = f'''На **19.12.2026, 13:00 (+03:00), по симулированным часам**, меняется поддержка отдельных обещаний. Новых испытаний нет; прежний выбор `OWNER-01` сохранён.

**Familiar:** отозвана поддержка «получателю не нужен аккаунт». Это не доказывает, что аккаунт обязателен. Семидневный срок этим сообщением не отозван, но остаётся непроверенным описанием. Основание: [заметка v1]({P}/inbox/q2/familiar-withdrawal-v1.txt), строки 1–4; S001@1, `physical-page:1/block:5`.

- **Продукт:** оставить исходящее предложение с ручной помощью гипотезой; убрать получение без аккаунта из поддерживаемых обещаний до приёмки. [Поправка]({F}/outputs/q2/product-strategy-amendment-v1.md).
- **Сообщение:** «Предлагаем проверить передачу комплекта по ссылке с ручной помощью. Порядок доступа получателя подтвердим до приглашения участников». Это внутренний черновик. [Поправка]({F}/outputs/q2/communication-strategy-amendment-v1.md).
- **Проверка:** на конкретной версии и разрешённом файле проверить получение и скачивание в чистой сессии без авторизации; зафиксировать необходимость входа, шаги и ошибки. Возможное трение получателя учитывать отдельно от времени отправителя. [Поправка]({F}/outputs/q2/validation-plan-amendment-v1.md).

**Variant:** отозвана поддержка «ссылки истекают через семь дней». Фактический срок неизвестен; бессрочность или другой срок из отзыва не следуют. Отсутствие аккаунта получателя явно не отозвано, но также требует приёмки. Основание: [заметка v1]({P}/inbox/q2/variant-withdrawal-v1.txt), строки 1–4; тот же блок S001@1.

- **Продукт:** сохранить гипотезу исходящего предложения, убрать гарантированный семидневный срок; автоматическое истечение и ручной отзыв проверять отдельно. [Поправка]({V}/outputs/q2/product-strategy-amendment-v1.md).
- **Сообщение:** «Предлагаем проверить передачу комплекта по ссылке с ручной помощью. Подтверждённый срок доступа сообщим после проверки конкретной версии». Это внутренний черновик. [Поправка]({V}/outputs/q2/communication-strategy-amendment-v1.md).
- **Проверка:** зафиксировать настройки, время создания и доступность ссылки до/после проверяемой границы. Связку «отправка до дня 23 + семь суток → завершение к дню 30» пока нельзя считать выполнимой. Семь суток наблюдения доставки не доказывают такой же срок жизни ссылки; календарь пересогласовывается после приёмки. Отдельное 30-дневное окно первой оплаты сохраняется как правило. [Поправка]({V}/outputs/q2/validation-plan-amendment-v1.md), уточнение к `outputs/v2/validation-plan.md`, «Календарь и окна».

**Сохраняются** внутренний режим, альтернативы выбора, воронка и сценарная экономика: новых значений XLSX нет, пересчёт не нужен. В частности, S002@2, `'Экономика'!E3`, остаётся 90 минут; C013/C014 и ECON-v2 переиспользованы с прежними хешами. `K-PROTOCOL` выполнен; `K-CAPABILITY` остаётся просроченным, `K-BUDGET` и `K-VALUE` — заблокированными без назначенных ответственных и дат. Завершившееся плановое окно `M-TIME` по-прежнему не подтверждает старт или результат.

**Сопровождение:** в обеих ветках аналитический пересмотр получил `revised`, а `owner_review_required=true` сохранён. После протокола приёмки владелец должен отдельно решить пригодность уточнённого предложения, бюджет и календарь; снять требование пересмотра может новая инструкция выбора с `resolves_reviews`. Нового выбора, реального запуска или внешних сообщений не было. Основания и передача контекста: [familiar]({F}/notes/q2/handoff-v1.md), [variant]({V}/notes/q2/handoff-v1.md); authoritative записи — revision 4, `decision.reviews/commitments/history`.

Ограничения утилиты зафиксированы: граф не различает две фразы одного PDF-блока, а необёрнутый отчёт impact может принять за расчёт. Одна ошибка подготовки устранена до публикации, исходные файлы сохранены; код утилит не менялся. [Диагностика]({F}/notes/q2/review-v1.md), `Q2-SCOPE/Q2-TOOL`.

Обе revision 4 повторно загружены, события подтверждены как `published`; q1 не изменён. Полный первый ответ — [q2.md]({P}/responses/q2.md), метаданные — [q2-meta.json]({P}/responses/q2-meta.json).
'''

responses = Path('responses')
with (responses / 'q2.md').open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(response)
assert (responses / 'q2.md').read_text(encoding='utf-8') == response
with (responses / 'q2-verification.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(verification, stream, ensure_ascii=False, indent=2)
    stream.write('\n')

logs = []
for record_path in sorted(Path('logs').glob('q2-*/result.json')):
    logs.append({'label': record_path.parent.name, **json.loads(record_path.read_text(encoding='utf-8'))})
started = min(row['started_at'] for row in logs)
ended = datetime.now(timezone.utc).isoformat()
meta = {
    'request': 'q2', 'participant': 'A', 'workspace': str(ROOT),
    'started_at_utc': started, 'ended_at_utc': ended,
    'time_scope': 'Начало — capture чтения request-q2.txt; конец — запись метаданных после проверки и сохранения ответа, перед выводом. Интервал не равен активному reasoning или времени человека.',
    'observed_interval_seconds': (datetime.fromisoformat(ended) - datetime.fromisoformat(started)).total_seconds(),
    'simulated_as_of': '2026-12-19T13:00:00+03:00', 'megafon_project_rules_present': True,
    'model': None, 'tokens': None, 'charges': None, 'human_minutes': None,
    'unknown_resources_note': 'Точные значения не предоставлены. Модель и settings не менялись.',
    'errors_and_repeats': [
        {'kind': 'prepare_assertion_failure', 'capture_label': 'q2-prepare', 'attempts_failed': 1,
         'detail': 'impact для draft с зарегистрированным raw impact добавил artifact:Q2-RAW-IMPACT как расчёт из S001. AssertionError остановил выполнение до новых outputs/state.',
         'resolution': 'Обе current остались revision 3; reconcile absent_from_current, новых outputs/final draft не было. Сохранены исходный script/report/draft. Создан новый Q2-IMPACT-RECORD с точным вложенным report и новый base-v2; подготовка q2-prepare-v2 выполнена один раз успешно. Штатные утилиты не изменялись.'},
        {'kind': 'graph_granularity', 'detail': 'Обе фразы находятся в одном PDF-блоке, граф дал одинаковые 16 узлов. По смыслу вручную разделены последствия доступа и срока/календаря; все узлы получили revised либо reviewed_unchanged.'},
        {'kind': 'display_truncation', 'detail': 'Выводы CLI load/save/view ограничены в отображении; capture сохранил полный stdout/stderr. Точные поля проверены API loader/reconcile/followup_view.'},
    ],
    'external_help': [{'kind': 'parent_coordinator_task_relay', 'detail': 'Передано поручение продолжить в той же папке и прочитать request-q2.txt; содержательных подсказок и доступа к чужим материалам не было.'}],
    'subagents_spawned': 0, 'live_web_used': False, 'other_external_services_used': [],
    'reads_outside_capture': [],
    'writes_outside_capture': [
        {'tool': 'apply_patch', 'path': 'q2-assess.py'},
        {'tool': 'apply_patch', 'path': 'q2-prepare.py'},
        {'tool': 'apply_patch', 'path': 'q2-recover-prepare.py'},
        {'tool': 'apply_patch', 'path': 'q2-finalize.py'},
    ],
    'writes_inside_capture_note': 'q2-prepare-v2.py создан q2-recover-prepare; все project artifacts/drafts/state и responses записаны через capture. Исходный q2-prepare.py сохранён.',
    'shell_workdir_explicit_in_every_call': True,
    'capture': {
        'completed_records_before_this_command': len(logs),
        'sum_completed_subprocess_elapsed_seconds': sum(row['elapsed_seconds'] for row in logs),
        'failed_completed_commands': [row['label'] for row in logs if row['returncode'] != 0],
        'records': logs, 'current_finalization_label': 'q2-finalize',
        'finalization_note': 'Текущий stdout/stderr/result сохранятся в logs/q2-finalize по завершении; elapsed этой команды ещё не включён в сумму.',
    },
    'verification': verification,
    'answer': {'path': 'responses/q2.md', 'sha256': hashlib.sha256((responses / 'q2.md').read_bytes()).hexdigest(), 'immutable_first_final_response': True},
    'q1_unchanged': True, 'state_writers': 1, 'business_choice_added': False,
    'real_world_actions_performed': False, 'analytical_review': 'revised', 'owner_review_required': True,
}
with (responses / 'q2-meta.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(meta, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
assert json.loads((responses / 'q2-meta.json').read_text(encoding='utf-8'))['answer']['sha256'] == meta['answer']['sha256']
print(json.dumps({'saved_answer': 'responses/q2.md', 'answer_sha256': meta['answer']['sha256'],
                  'meta': 'responses/q2-meta.json', 'ended_at_utc': ended,
                  'published_revisions': {b: v['revision'] for b, v in verification.items()},
                  'owner_review_required': True, 'q1_unchanged': True}, ensure_ascii=False, indent=2))
print(response)
