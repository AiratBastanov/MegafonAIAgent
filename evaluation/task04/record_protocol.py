"""Фиксация наблюдённого локального документа; не имитация выполнения пилота."""
import json
from project_io import PROJECT, ps, df, attach, publish
from observe import log

data = ps.load_state(PROJECT)
assert data['revision'] == 3
attach(data, 'evidence/followup-protocol-v1.md', 'FOLLOWUP-PROTOCOL')
data['resources'] = {'origin_accounting': 'ORIGIN-STATE/resources (TASK03, не интервал TASK04)',
                     'demonstration_started_at': '2026-11-16T11:53:16.190100+00:00',
                     'tokens': None, 'charges': None, 'human_minutes': None, 'exact_model_id': None,
                     'clock_note': 'Реальные timestamps действий в evaluation/task04/actions.jsonl; условия view используют явно simulated clock'}
event = dict(id='COMPLETE-PROTOCOL-01', project_id=PROJECT.name, kind='completion', at='2026-11-16T15:05:00+03:00',
             provenance={'kind': 'agent_review', 'artifact_id': 'FOLLOWUP-PROTOCOL', 'locator': 'весь документ'},
             commitment_id='K-PROTOCOL', completion_evidence=[{'artifact_id': 'FOLLOWUP-PROTOCOL', 'locator': 'абзацы 1–5'}],
             completion_check='Координатор проверил: документ отделяет learning/scaling, перечисляет неизвестные, запрещает фактический запуск; это определение K-PROTOCOL, не K-CAPABILITY')
# at выше — время события внутри синтетического сценария; время исполнения log фактическое.
data, _ = df.apply_event(PROJECT, data, event)
data['stage'] = 'decision_followup'
data['next_action'] = 'Владелец симуляции должен выбрать: требовать приёмку и назначить ответственного за бюджет либо продолжить внутренний режим; реальных доказательств нет'
saved = publish(data, 'protocol-completed-v1')
log('host_observation', project_id=PROJECT.name, revision=saved['revision'],
    observed='Завершён только K-PROTOCOL по существующему документу. Протокол приёмки, бюджет, рынок и платежи не созданы.')
print(json.dumps({'revision': saved['revision'], 'completed': ['K-PROTOCOL'], 'operational_progress': False}, ensure_ascii=False))
