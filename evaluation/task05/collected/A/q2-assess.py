"""Register only new inputs and calculate declared impact, without publishing."""
import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path('scripts').resolve()))
import project_state as ps
import decision_followup as df
import import_materials as importer

AS_OF = '2026-12-19T13:00:00+03:00'


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


q1_hashes = {name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
             for name in ('responses/q1.md', 'responses/q1-meta.json')}
assert q1_hashes['responses/q1.md'] == '1c304850525bd58afce0b09a5026321cb2ba6bf3a6b435f4621f86d802000fe0'

for branch, phrase, unknown in (
    ('familiar', 'recipient needs no account', 'Не установлено, требуется ли получателю аккаунт.'),
    ('variant', 'links expire after 7 days', 'Фактический срок жизни ссылки неизвестен.'),
):
    root = Path('branches') / branch / 'projects/task04-followup'
    baseline = ps.load_state(root)
    assert baseline['revision'] == 3
    assert df.reconcile(root, 'Q1-K-PROTOCOL-COMPLETE')['outcome'] == 'published'
    data = copy.deepcopy(baseline)
    incoming = Path('inbox/q2') / (branch + '-withdrawal-v1.txt')
    relative_input = 'inputs/q2/withdrawal-v1.txt'
    target = root / relative_input
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(incoming.read_bytes())
    registration = importer.register(
        root, 'Q2-WITHDRAWAL', relative_input, 'text',
        origin=incoming.as_posix() + '; supplied synthetic author note',
        synthetic=True, locator='line:1-4',
        limitations=['Отозвана поддержка указанной фразы, не сообщён результат испытания; это не доказательство противоположного поведения.'],
    )
    assert registration['source']['version'] == 1 and not registration['reused']
    refs = []
    for suffix, filename in (('meta', 'source.json'), ('original', 'original.txt'), ('extract', 'extract.json')):
        aid = 'Q2-WITHDRAWAL-v1-' + suffix
        data['artifacts'].append(ps.reference(root, 'evidence/sources/Q2-WITHDRAWAL/v1/' + filename, aid))
        refs.append(aid)
    data['sources'].append({'id': 'Q2-WITHDRAWAL', 'version': 1, 'synthetic': True, 'artifact_ids': refs})

    event = {
        'id': 'Q2-' + branch.upper() + '-WITHDRAWAL',
        'project_id': 'task04-followup', 'kind': 'evidence_change',
        'at': AS_OF, 'clock': 'simulated',
        'provenance': {'kind': 'source_material', 'artifact_id': 'Q2-WITHDRAWAL-v1-extract', 'locator': 'line:1-4'},
        'change': {
            'type': 'withdrawn_support', 'source': {'id': 'S001', 'version': 1},
            'locators': ['physical-page:1/block:5'], 'withdrawn_text': phrase,
            'reason': 'Автор отозвал поддержку только фразы ' + phrase + '; протокол и новые результаты не представлены.',
            'old_ground': 'S001@1, physical-page:1/block:5, сообщал: ' + phrase + '. Производственной приёмки не было.',
            'new_ground': 'Текущая поддержка этой фразы отозвана. ' + unknown + ' Историческое содержание PDF сохраняется.',
            'applicability': 'Меняет допустимое обещание и условия проверки исходящего предложения; остальные фразы того же блока, таблица и экономика не изменены.'
        }
    }
    write_json(root / 'inputs/q2/evidence-change-v1.json', event)
    data['artifacts'].append(ps.reference(root, 'inputs/q2/evidence-change-v1.json', 'Q2-EVIDENCE-CHANGE'))
    ps.validate_state(root, data)
    report = df.impact(root, data, event)
    write_json(root / 'notes/q2/raw-impact-v1.json', report)
    data['artifacts'].append(ps.reference(root, 'notes/q2/raw-impact-v1.json', 'Q2-RAW-IMPACT'))
    write_json(root / 'notes/q2/baseline-v1.json', {
        'revision': baseline['revision'], 'state_sha256': baseline['state_sha256'],
        'q1_response_hashes': q1_hashes, 'q1_completion_reconciled': 'published',
    })
    data['artifacts'].append(ps.reference(root, 'notes/q2/baseline-v1.json', 'Q2-BASELINE'))
    ps.validate_state(root, data)
    write_json(root / 'drafts/q2-evidence-base-v1.json', data)
    affected_claim_ids = {item['node'][6:] for item in report['affected'] if item['node'].startswith('claim:')}
    print(json.dumps({
        'branch': branch, 'basis_revision': baseline['revision'],
        'event': event, 'affected': report['affected'], 'precision': report['precision'],
        'affected_claims_before': [c for c in baseline['claims'] if c['id'] in affected_claim_ids],
        'status': 'impact_only_not_applied_not_published',
    }, ensure_ascii=False, indent=2))
