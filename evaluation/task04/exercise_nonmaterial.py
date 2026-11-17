"""Наблюдение no-op/replay/scope без перезаписи стратегий."""
import copy
import hashlib
import json
from project_io import PROJECT, ROOT, ps, df, attach, register_source, publish, event_file
from observe import write_new, log, manifest

data = ps.load_state(PROJECT)
assert data['revision'] == 9
before_outputs = {a['id']: a['sha256'] for a in data['artifacts'] if a['id'].startswith('OUTPUT-v3-')}
before_claims = copy.deepcopy(data['claims'])
canonical_before = {p: manifest(p) for p in ['projects/demo-001', 'projects/demo-002', 'evaluation/task03/continuation-workspace']}
register_source(data, 'S007', 1)
attach(data, 'evidence/nonmaterial-review-v1.md', 'NONMATERIAL-REVIEW')
event = dict(id='NONMATERIAL-01', project_id=PROJECT.name, kind='evidence_change', clock='simulated', at='2026-11-19T12:00:00+03:00',
             provenance={'kind': 'source_material', 'artifact_id': 'S007v1-extract', 'locator': 'line:1-2'},
             change=dict(type='nonmaterial', source={'id': 'S007', 'version': 1}, locators=['line:1-2'],
                         reason='Внутренняя служебная подпись не меняет оснований решения', old_ground='Служебная подпись',
                         new_ground='Уточнённая подпись журнала', applicability='Не относится к бизнес-вопросу и не используется в объявленных связях'))
write_new(PROJECT / 'inputs/nonmaterial-event-v1.json', event)
data, _ = df.apply_event(PROJECT, data, event)
assert data['decision']['reviews'][-1]['impact']['affected'] == []
resolution = dict(id='REVIEW-NONMATERIAL-01', project_id=PROJECT.name, kind='review', clock='simulated', at=event['at'],
                  provenance={'kind': 'agent_review', 'artifact_id': 'NONMATERIAL-REVIEW', 'locator': 'весь документ'}, review_id='review-NONMATERIAL-01',
                  resolution=dict(status='reviewed_unchanged', reason='Материал не применим к бизнес-основаниям; affected пуст, стратегии/обязательства не меняются',
                                  owner_review_required=False, next_action='Продолжить открытый пересмотр WITHDRAW-01',
                                  resolution_evidence=[{'artifact_id': 'NONMATERIAL-REVIEW', 'locator': 'весь документ'}]))
data, _ = df.apply_event(PROJECT, data, resolution)
assert data['claims'] == before_claims
saved = publish(data, 'nonmaterial-reviewed-v1')
for path in ['inputs/owner-choice-v1.json', 'inputs/withdrawal-event-v1.json', 'inputs/nonmaterial-event-v1.json']:
    identical, changed = df.apply_event(PROJECT, saved, event_file(path))
    assert not changed and identical == saved
foreign = copy.deepcopy(event)
foreign['project_id'] = 'demo-001'
try:
    df.apply_event(PROJECT, saved, foreign)
    raise AssertionError('Scope escape accepted')
except df.FollowupError:
    pass
assert all(manifest(p) == records for p, records in canonical_before.items())
assert len(saved['decision']['history']) == 1 and len(saved['decision']['commitments']) == 4
after_outputs = {a['id']: a['sha256'] for a in saved['artifacts'] if a['id'].startswith('OUTPUT-v3-')}
assert after_outputs == before_outputs
checks = {'revision': saved['revision'], 'affected': [], 'identical_replays': ['OWNER-01', 'WITHDRAW-01', 'NONMATERIAL-01'],
          'decision_count': 1, 'commitment_count': 4, 'outputs_unchanged': before_outputs, 'claims_unchanged': True,
          'foreign_project_rejected': True, 'canonical_and_continuation_unchanged': True}
write_new(PROJECT / 'evidence/nonmaterial-check-v1.json', checks)
log('nonmaterial_and_replay_observed', project_id=PROJECT.name, **checks)
print(json.dumps(checks, ensure_ascii=False, indent=2))
