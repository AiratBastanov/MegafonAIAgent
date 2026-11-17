"""Закрепить содержательный вывод координатора после наблюдённого numeric impact."""
import copy
import json
from project_io import PROJECT, ps, df, attach, publish
from observe import write_new, log

data = ps.load_state(PROJECT)
assert data['revision'] == 8
before = ps._read_json(PROJECT / 'state/history/r000007.json', ps.DEFAULT_MAX_BYTES)
old_claims = {c['id']: c for c in before['claims']}
for claim in data['claims']:
    if claim.get('support_reason', '').startswith('ECON-RECHECK-01:'):
        for field in ('status', 'support_reason'):
            if field in old_claims[claim['id']]:
                claim[field] = old_claims[claim['id']][field]
            else:
                claim.pop(field, None)
attach(data, 'evidence/economic-review-v1.md', 'ECON-REVIEW')
query = dict(id='CURRENT-ECON-SCOPE', project_id=PROJECT.name, kind='evidence_change', at='2026-11-19T11:00:00+03:00', clock='simulated',
             provenance={'kind': 'agent_review', 'artifact_id': 'ECON-REVIEW', 'locator': 'абзац 3'},
             change=dict(type='changed_assumption', source={'id': 'S002', 'version': 2}, locators=["'Экономика'!E3"],
                         reason='Контрольный вопрос: что пересмотреть при будущем уточнении действующего значения?',
                         old_ground='90 минут текущего условного сценария', new_ground='Новое значение неизвестно; это только запрос охвата',
                         applicability='Только проверка объявленной связи текущей версии, без регистрации нового факта'))
scope = df.impact(PROJECT, data, query)
path = next(x['path'] for x in scope['affected'] if x['node'] == 'claim:C011')
assert 'claim:C014' in path or 'claim:C013' in path
write_new(PROJECT / 'evidence/current-economic-scope-v1.json', scope)
attach(data, 'evidence/current-economic-scope-v1.json', 'CURRENT-ECON-SCOPE')
event = dict(id='REVIEW-ECON-01', project_id=PROJECT.name, kind='review', at='2026-11-19T11:00:00+03:00', clock='simulated',
             provenance={'kind': 'agent_review', 'artifact_id': 'ECON-REVIEW', 'locator': 'весь документ'}, review_id='review-ECON-RECHECK-01',
             resolution=dict(status='reviewed_unchanged', reason='Текущий выбор и v3 уже используют исправленные 90 минут/нулевой остаток; воронка и текущая экономика переиспользованы после сверки',
                             owner_review_required=True, next_action='Учитывать подтверждённое ограничение экономики при открытом пересмотре владельцем; реальные затраты и продления ещё нужны',
                             resolution_evidence=[{'artifact_id': 'ECON-RECHECK', 'locator': 'values.1,values.2,passed'},
                                                  {'artifact_id': 'ECON-REVIEW', 'locator': 'весь документ'}]))
data, _ = df.apply_event(PROJECT, data, event)
saved = publish(data, 'economic-reviewed-unchanged-v1')
log('host_analysis', project_id=PROJECT.name, revision=saved['revision'], outcome='reviewed_unchanged',
    current_economic_review_path=path, outputs_rewritten=False, input_reimported=False)
print(json.dumps({'revision': saved['revision'], 'current_path_to_C011': path, 'outputs': 'v3 unchanged'}, ensure_ascii=False))
