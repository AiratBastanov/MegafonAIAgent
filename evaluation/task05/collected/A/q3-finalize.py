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
    root = Path('branches') / branch / 'projects/task04-followup'
    current = ps.load_state(root)
    previous = json.loads((root / 'state/previous.json').read_text(encoding='utf-8'))
    ps.validate_state(root, previous, require_saved=True)
    initial = json.loads((Path('logs') / ('q3-' + branch + '-load') / 'stdout.txt').read_text(encoding='utf-8'))['state']
    assert previous == initial and current['revision'] == 5 and previous['revision'] == 4
    for field in previous:
        if field not in {'artifacts', 'sources', 'revision', 'saved_at', 'state_sha256'}:
            assert current[field] == previous[field], field
    assert current['artifacts'][:len(previous['artifacts'])] == previous['artifacts']
    assert current['sources'][:len(previous['sources'])] == previous['sources']
    assert len(current['sources']) - len(previous['sources']) == 2
    assert len(current['artifacts']) - len(previous['artifacts']) == 8
    receipt = json.loads((root / 'notes/q3/receipt-v1.json').read_text(encoding='utf-8'))
    for name, expected_hash in receipt['previous_response_hashes'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected_hash
    review = current['decision']['reviews'][0]
    assert review['id'] == 'review-Q2-' + branch.upper() + '-WITHDRAWAL'
    assert review['status'] == 'revised' and review['owner_review_required'] is True
    view = df.followup_view(current, '2026-12-19T14:00:00+03:00', '+03:00', 'simulated')
    commitments = {c['id']: c for c in view['commitments']}
    assert commitments['K-PROTOCOL']['status'] == 'completed'
    assert commitments['K-CAPABILITY']['attention'] == ['overdue']
    assert all(commitments[c]['attention'] == ['unassigned', 'blocked'] for c in ('K-BUDGET', 'K-VALUE'))
    assert view['metrics'][0]['window_state'] == 'ended_evidence_required'
    verification[branch] = {
        'revision': 5, 'state_sha256': current['state_sha256'],
        'previous_revision': 4, 'previous_state_sha256': previous['state_sha256'],
        'changes_only': ['two incoming source receipts', 'eight artifact references', 'state publication metadata'],
        'decision_claims_commitments_metrics_outputs_unchanged': True,
        'new_events': 0, 'new_reviews': 0, 'new_commitments': 0,
        'review_id': review['id'], 'review_status': 'revised', 'owner_review_required': True,
        'q1_q2_answer_and_meta_hashes_unchanged': receipt['previous_response_hashes'],
    }
    with (root / 'state/actions.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps({
            'at': datetime.now(timezone.utc).isoformat(), 'action': 'Q3 receipt publication verified',
            'revision': 5, 'state_sha256': current['state_sha256'],
            'outcome': 'load_valid; all substantive fields equal revision 4',
            'owner_review_required_preserved': True, 'new_events': 0,
            'previous_answers_unchanged': True, 'errors': [],
        }, ensure_ascii=False) + '\n')

response = f'''На **19.12.2026, 14:00 (+03:00), по симулированным часам**, **переписывать продуктовые документы, заводить обязательства или повторно запрашивать решение из-за этих сообщений не нужно**.

- [Повтор коррекции v2]({P}/inbox/q3/repeated-correction-v2.txt), строки 1–2, не содержит новых значений, XLSX, измерений или решения. 90 минут уже учтены в S002@2, `'Экономика'!E3`, C013/C014 и ECON-v2.
- [Административная заметка v1]({P}/inbox/q3/irrelevant-note-v1.txt), строки 1–3, касается папки иллюстраций; оснований решения, функций, затрат, сроков и обязательств она не меняет.

**Открытым остаётся прежний пересмотр q2**, а не новый запрос:

| Ветка | Что ещё требуется |
|---|---|
| `familiar` | Протокол фактического доступа получателя. Обещание «без аккаунта» остаётся неподтверждённым; обязательность аккаунта также не установлена. |
| `variant` | Протокол фактического срока и автоматического истечения ссылки отдельно от ручного отзыва; затем проверка пригодности календаря. Семь дней не подтверждены, другой срок неизвестен. |

В обеих ветках `review.status=revised`, **`owner_review_required=true`**: после приёмки нужно отдельное решение владельца об уточнённом предложении, бюджете и календаре. Новые заметки не закрывают это требование. Прежний `OWNER-01`, поправки q2 и внутренний режим сохраняются.

`K-CAPABILITY` остаётся просроченным; `K-BUDGET` и `K-VALUE` — заблокированными, без назначенных ответственных и дат. `K-PROTOCOL` выполнен. Плановое окно `M-TIME` истекло, но старт и результаты не сообщались; остальные фактические окна неизвестны. Проверка актуальности S003/S004 перед следующим сравнением также остаётся открытой. Основания: сохранённые записи `decision.reviews/commitments/metrics/conditions`; краткая передача для [familiar]({F}/notes/q3/handoff-v1.md) и [variant]({V}/notes/q3/handoff-v1.md).

В revision 5 обеих веток добавлены только записи о получении и короткая передача контекста; содержательные поля совпадают с revision 4. Повторная загрузка прошла, ответы q1/q2 не изменены. Первый ответ сохранён в [q3.md]({P}/responses/q3.md), метаданные — в [q3-meta.json]({P}/responses/q3-meta.json).
'''

with Path('responses/q3.md').open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(response)
assert Path('responses/q3.md').read_text(encoding='utf-8') == response
logs = [{'label': record_path.parent.name, **json.loads(record_path.read_text(encoding='utf-8'))}
        for record_path in sorted(Path('logs').glob('q3-*/result.json'))]
started = min(row['started_at'] for row in logs)
ended = datetime.now(timezone.utc).isoformat()
meta = {
    'request': 'q3', 'participant': 'A', 'workspace': str(ROOT),
    'started_at_utc': started, 'ended_at_utc': ended,
    'time_scope': 'От capture чтения request-q3.txt до записи метаданных после проверки и сохранения ответа. Это наблюдаемый интервал, не активное reasoning или время человека.',
    'observed_interval_seconds': (datetime.fromisoformat(ended) - datetime.fromisoformat(started)).total_seconds(),
    'simulated_as_of': '2026-12-19T14:00:00+03:00',
    'megafon_project_rules_present': True,
    'model': None, 'tokens': None, 'charges': None, 'human_minutes': None,
    'unknown_resources_note': 'Не предоставлены; settings и модель не менялись.',
    'errors_and_repeats': [
        {'kind': 'incoming_duplicate', 'detail': 'Повтор S005@1 классифицирован как отсутствие существенного изменения. Исходные S001/S002/S005 не импортировались повторно; расчёты и рабочие документы не менялись.'},
        {'kind': 'display_truncation', 'detail': 'Большие CLI load/save/view усечены только в отображении. Полные stdout/stderr сохранены capture; точные поля проверены загрузкой и сравнением с revision 4.'},
    ],
    'failed_attempts': 0, 'repeated_shell_attempts': 0,
    'external_help': [{'kind': 'parent_coordinator_task_relay', 'detail': 'Передано поручение продолжить в той же рабочей папке и прочитать request-q3.txt. Содержательных подсказок не было.'}],
    'subagents_spawned': 0, 'live_web_used': False, 'other_external_services_used': [],
    'reads_outside_capture': [],
    'writes_outside_capture': [
        {'tool': 'apply_patch', 'path': 'q3-prepare.py'},
        {'tool': 'apply_patch', 'path': 'q3-finalize.py'},
    ],
    'shell_workdir_explicit_in_every_call': True,
    'capture': {
        'completed_records_before_this_command': len(logs),
        'sum_completed_subprocess_elapsed_seconds': sum(row['elapsed_seconds'] for row in logs),
        'failed_completed_commands': [row['label'] for row in logs if row['returncode'] != 0],
        'records': logs, 'current_finalization_label': 'q3-finalize',
        'finalization_note': 'Текущие stdout/stderr/result появятся в logs/q3-finalize после завершения; elapsed этой команды ещё не включён в сумму.',
    },
    'verification': verification,
    'answer': {'path': 'responses/q3.md', 'sha256': hashlib.sha256(Path('responses/q3.md').read_bytes()).hexdigest(), 'immutable_first_final_response': True},
    'previous_answers_unchanged': True, 'state_writers': 1,
    'new_business_choice': False, 'new_commitments': 0, 'new_owner_request': False,
    'existing_owner_review_required_preserved': True, 'real_world_actions_performed': False,
}
with Path('responses/q3-meta.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(meta, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
assert json.loads(Path('responses/q3-meta.json').read_text(encoding='utf-8'))['answer']['sha256'] == meta['answer']['sha256']
print(json.dumps({'saved_answer': 'responses/q3.md', 'answer_sha256': meta['answer']['sha256'],
                  'meta': 'responses/q3-meta.json', 'ended_at_utc': ended,
                  'published_revisions': {b: v['revision'] for b, v in verification.items()},
                  'substantive_state_unchanged': True, 'q1_q2_unchanged': True}, ensure_ascii=False, indent=2))
print(response)
