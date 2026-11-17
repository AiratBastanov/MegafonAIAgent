"""Изолированные диагностические примеры; исходные проекты не изменяются."""
from pathlib import Path
import copy
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import project_state as ps
import import_materials as im
import decision_followup as df

BASE = Path(__file__).parent

def seed(name):
    project = BASE / name
    project.mkdir()
    (project / 'input.txt').write_text('Учебное наблюдение: 5 из 20.\n', encoding='utf-8')
    reg = im.register(project, 'S', 'input.txt', 'text', synthetic=True)
    data = dict(schema_version=1, project_id=name, objective='Изолированная проверка',
                decision_question='Продолжать?', stage='research_complete', next_action='Проверить',
                completed=[], unresolved_questions=[], pending_actions=[], artifacts=[], sources=[],
                claims=[], decision={'status': 'proposed'})
    for aid, path in [('META', reg['record']['path']), ('ORIGINAL', reg['source']['original']['path']),
                      ('EXTRACT', reg['source']['extract']['path'])]:
        data['artifacts'].append(ps.reference(project, path, aid))
    data['sources'] = [dict(id='S', version=1, synthetic=True, artifact_ids=['META', 'ORIGINAL', 'EXTRACT'])]
    data['claims'] = [dict(id='C', kind='source_fact', text='Источник сообщает 5 из 20', synthetic=True,
                          evidence=[dict(artifact_id='EXTRACT', locator='line:1', source_id='S', source_version=1)],
                          derived_from=[])]
    return project, data

results = {}
project, data = seed('stale-probe')
first = ps.save_state(project, data)
second = copy.deepcopy(first)
second['completed'].append('Полезный шаг r2')
second['next_action'] = 'Сохранённое новое действие r2'
ps.save_state(project, second)
stale = copy.deepcopy(first)
stale['stage'] = 'old_draft_processed'
third = ps.save_state(project, stale)
results['stale_update'] = dict(published_revision=third['revision'],
                              lost_committed_action='Полезный шаг r2' not in third['completed'],
                              current_next_action=third['next_action'])

project, data = seed('synthetic-probe')
data['sources'][0]['synthetic'] = False
data['claims'][0]['synthetic'] = False
ps.validate_state(project, data)
results['synthetic_downgrade'] = dict(accepted=True, metadata_synthetic=True,
                                    declared_source_synthetic=False, declared_claim_synthetic=False)

project, data = seed('completion-probe')
data['decision'] = dict(format_version=2, status='awaiting_decision', question='Продолжать?',
                       proposed_option='Проверить', owner='unassigned', history=[], events=[], commitments=[],
                       metrics=[], conditions=[], reviews=[])
first = ps.save_state(project, data)
choice = dict(id='CHOICE', project_id=project.name, at='2026-11-17T09:00:00+03:00', kind='choice',
              provenance=dict(kind='user_instruction', artifact_id='ORIGINAL', locator='line:1'),
              authorized=True, actor='Искусственный участник теста',
              choice=dict(question='Продолжать?', option='Проверить', reason='Тест', owner='Тестовая роль',
                          rejected_alternatives=[dict(option='Закрыть', reason='Тест')], ground_ids=['C']),
              commitments=[dict(id='K', description='Выполнить проверку', owner='Тестовая роль', due_at=None,
                                due_condition='До проверки', required_evidence='Результат фактической проверки',
                                status='pending', condition_ids=[], blocked_by=[], completion_evidence=[])])
candidate, _ = df.apply_event(project, first, choice)
accepted = ps.save_state(project, candidate)
completion = dict(id='COMPLETE', project_id=project.name, at='2026-11-17T10:00:00+03:00', kind='completion',
                  provenance=dict(kind='synthetic_instruction', artifact_id='ORIGINAL', locator='line:1'),
                  commitment_id='K', completion_check='Искусственная проверка',
                  completion_evidence=[dict(artifact_id='ORIGINAL', locator='line:1')])
candidate, _ = df.apply_event(project, accepted, completion)
saved = ps.save_state(project, candidate)
results['synthetic_completion_outside_evaluation'] = dict(accepted=True, evaluation=saved.get('evaluation'),
       choice_status=saved['decision']['status'], commitment_status=saved['decision']['commitments'][0]['status'])
(BASE / 'probe-results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(results, ensure_ascii=False, indent=2))
