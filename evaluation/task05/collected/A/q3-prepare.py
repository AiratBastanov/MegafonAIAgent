"""Record receipt and a minimal handoff without changing decisions or work items."""
import copy
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path('scripts').resolve()))
import project_state as ps
import decision_followup as df
import import_materials as importer

AS_OF = '2026-12-19T14:00:00+03:00'


def write_new(path, value, is_json=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n' if is_json else value)


answer_hashes = {name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
                 for name in ('responses/q1.md', 'responses/q1-meta.json',
                              'responses/q2.md', 'responses/q2-meta.json')}
assert answer_hashes['responses/q1.md'] == '1c304850525bd58afce0b09a5026321cb2ba6bf3a6b435f4621f86d802000fe0'
assert answer_hashes['responses/q2.md'] == 'fd0aec4b1b1c3979be813734c264f4a7d3e084fdb6947005ebca077c611ae81e'

for branch, open_issue, next_step in (
    ('familiar', 'доступ получателя без аккаунта не подтверждён',
     'Получить протокол фактического доступа/скачивания получателя и затем решение владельца по уточнённому предложению.'),
    ('variant', 'семидневный срок ссылки не подтверждён',
     'Получить протокол фактического срока/автоматического истечения отдельно от ручного отзыва, затем решение владельца по предложению и календарю.'),
):
    root = Path('branches') / branch / 'projects/task04-followup'
    baseline = ps.load_state(root)
    assert baseline['revision'] == 4
    review_id = 'review-Q2-' + branch.upper() + '-WITHDRAWAL'
    existing_review = next(r for r in baseline['decision']['reviews'] if r['id'] == review_id)
    assert existing_review['status'] == 'revised' and existing_review['owner_review_required'] is True
    data = copy.deepcopy(baseline)
    baseline_artifact_paths = [a['path'] for a in baseline['artifacts']]
    assert not any('slides-art' in path for path in baseline_artifact_paths)
    extract = json.loads((root / 'evidence/sources/S002/v2/extract.json').read_text(encoding='utf-8'))
    e3 = [c for s in extract['sheets'] for c in s['cells'] if c['locator'] == "'Экономика'!E3"]
    assert len(e3) == 1 and e3[0]['value'] == 90

    for sid, filename, classification in (
        ('Q3-REPEAT', 'repeated-correction-v2.txt', 'Повтор уже учтённой S005@1; не новая версия XLSX и не новое решение.'),
        ('Q3-ADMIN', 'irrelevant-note-v1.txt', 'Административная заметка о папке иллюстраций; не меняет рассматриваемое основание решения или зарегистрированные рабочие пути.'),
    ):
        incoming = Path('inbox/q3') / filename
        relative_input = 'inputs/q3/' + filename
        destination = root / relative_input
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as stream:
            stream.write(incoming.read_bytes())
        registered = importer.register(
            root, sid, relative_input, 'text', origin=incoming.as_posix() + '; supplied synthetic note',
            synthetic=True, locator='line:1-2' if sid == 'Q3-REPEAT' else 'line:1-3',
            limitations=[classification, 'Регистрация получения не создаёт независимого подтверждения продукта, результата или полномочий.'],
        )
        assert not registered['reused'] and registered['source']['version'] == 1
        aids = []
        for suffix, name in (('meta', 'source.json'), ('original', 'original.txt'), ('extract', 'extract.json')):
            aid = sid + '-v1-' + suffix
            data['artifacts'].append(ps.reference(root, 'evidence/sources/' + sid + '/v1/' + name, aid))
            aids.append(aid)
        data['sources'].append({'id': sid, 'version': 1, 'synthetic': True, 'artifact_ids': aids})

    view = df.followup_view(baseline, AS_OF, '+03:00', 'simulated')
    receipt = {
        'record_kind': 'receipt_and_applicability_assessment', 'branch': branch,
        'as_of': AS_OF, 'clock': 'simulated', 'basis_revision': 4,
        'basis_state_sha256': baseline['state_sha256'],
        'inputs': [
            {'source_id': 'Q3-REPEAT', 'source_version': 1, 'locator': 'line:1-2',
             'classification': 'duplicate_no_material_change',
             'reason': 'Сообщены те же 90 вместо 30 минут, без новых значений, XLSX, измерений или выбора. Проверена S002@2, Экономика!E3=90; C013/C014 и ECON-v2 уже учитывают S005@1.'},
            {'source_id': 'Q3-ADMIN', 'source_version': 1, 'locator': 'line:1-3',
             'classification': 'irrelevant_to_decision',
             'reason': 'Папка обложечных иллюстраций не является источником или обязательством продукта. В текущем реестре artifact paths нет slides-art; заметка прямо сохраняет функции, затраты, обязательства, сроки и решения. Переименовывать локальные файлы по ней не требуется.'},
        ],
        'decision_effect': 'none', 'new_commitments': [], 'new_reviews': [], 'new_owner_request': False,
        'review_kept_open': {'id': review_id, 'status': 'revised', 'owner_review_required': True},
        'new_evidence_change_event': None,
        'event_reason': 'Нет изменения основания. Не создаём ложное evidence_change через широкое прохождение nonmaterial; существующий Q2 review не закрываем и не дублируем.',
        'reuse': {'claims': 'unchanged', 'calculations': 'unchanged', 'current_outputs': baseline['decision']['current_outputs'],
                 'history': 'unchanged', 'commitments': 'unchanged', 'metrics': 'unchanged'},
        'attention_at_call': {c['id']: c['attention'] for c in view['commitments']},
        'metric_windows_at_call': {m['id']: m['window_state'] for m in view['metrics']},
        'remaining_next_step': next_step,
        'previous_response_hashes': answer_hashes,
        'limitations': 'Это классификация координатора по прочитанным материалам и проверенному state. Реального испытания, нового выбора или независимого ревью нет. Даты simulated; проверки только при вызове.',
    }
    write_new(root / 'notes/q3/receipt-v1.json', receipt, True)
    data['artifacts'].append(ps.reference(root, 'notes/q3/receipt-v1.json', 'Q3-RECEIPT'))

    handoff = f'''# Короткое дополнение к Q2 — {branch}, Q3 v1

На {AS_OF}, clock=simulated. Проверенная база — revision 4 / {baseline['state_sha256']}. Содержательная передача notes/q2/handoff-v1.md остаётся действующей.

Q3-REPEAT@1, line:1-2: повтор 90 минут, уже учтённых S005@1/S002@2, 'Экономика'!E3. Q3-ADMIN@1, line:1-3: заметка про slides-art не затрагивает решение или зарегистрированные рабочие пути. Зафиксировано только получение; новых claims/расчётов/outputs/обязательств/событий пересмотра/выбора нет. Не запрашивать решение повторно из-за этих сообщений.

Открыт прежний {review_id}: revised, owner_review_required=true; {open_issue}. Поправки outputs/q2 продолжают действовать. {next_step} Снять owner flag можно только новой инструкцией выбора с resolves_reviews=[{review_id}], не повтором коррекции или агентским review.

K-CAPABILITY pending/overdue; K-BUDGET/K-VALUE blocked/unassigned, даты неизвестны. K-PROTOCOL completed и неизменён. M-TIME — истёкший план без сообщённого старта/результатов; окна других метрик неизвестны. G-FRESHNESS остаётся требованием проверки перед следующим сравнением. Прежний OWNER-01 и внутренний режим сохранены, реального запуска/расходов/сообщений нет.

Проверка получения и неизменности: notes/q3/receipt-v1.json. Источники Q3 зарегистрированы как отдельные входящие заметки, не новые версии S001/S002/S005 и не независимые подтверждения. authoritative состояние проверять штатным load. Первые ответы q1/q2 не изменять; новый ответ и метаданные — package-root/responses/q3.md и q3-meta.json.
'''
    write_new(root / 'notes/q3/handoff-v1.md', handoff)
    data['artifacts'].append(ps.reference(root, 'notes/q3/handoff-v1.md', 'Q3-HANDOFF'))
    for field in baseline:
        if field not in {'artifacts', 'sources'}:
            assert data[field] == baseline[field], field
    ps.validate_state(root, data)
    df.validate_transition(baseline, data)
    write_new(root / 'drafts/q3-receipt-v1.json', data, True)
    with (root / 'state/actions.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps({
            'at': datetime.now(timezone.utc).isoformat(), 'action': 'Q3 classify two notes and preserve open Q2 review',
            'as_of': AS_OF, 'clock': 'simulated', 'basis_revision': 4,
            'outcome': 'receipt_candidate_validated_only_artifacts_and_source_receipts_added',
            'new_commitments': 0, 'new_reviews': 0, 'new_choice': False, 'owner_review_required_preserved': True,
            'errors': [], 'retries': 0, 'model': None, 'tokens': None, 'charges': None,
        }, ensure_ascii=False) + '\n')
    print(json.dumps({'branch': branch, 'validated': True, 'draft': 'drafts/q3-receipt-v1.json',
                      'substantive_state_unchanged': True, 'new_sources': ['Q3-REPEAT@1', 'Q3-ADMIN@1'],
                      'new_reviews': 0, 'new_commitments': 0, 'open_review': review_id,
                      'owner_review_required': True, 'publication': 'pending'}, ensure_ascii=False))
