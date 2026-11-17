"""Одно обоснованное исправление canonical metadata с сохранением истории."""
import shutil
import json
from project_io import ROOT, ps, attach, publish
from observe import manifest, write_new

project = ROOT / 'projects/demo-002'
data = ps.load_state(project)
assert data['revision'] == 4 and data['decision']['status'] == 'awaiting_decision'
before_outputs = manifest('projects/demo-002/outputs')
shutil.copyfile(project / 'README.md', project / 'evidence/readme-before-task04.md')
attach(data, 'evidence/readme-before-task04.md', 'README-BEFORE-TASK04', project)
attach(data, 'evidence/task04-dependency-review-v1.md', 'TASK04-DEPENDENCY-REVIEW', project)
for claim in data['claims']:
    if claim['id'] == 'C011':
        claim['review_dependencies'] = ['C013', 'C014']
    if claim['id'] in {'C006', 'C007'}:
        claim['derived_from'] = []
        claim['context_from'] = ['C003']
data['artifact_dependencies'] = [{'from': f'ECON-RAW-v{v}', 'to': f'ECON-v{v}',
                                 'reason': 'Сценарный расчёт использует literal значения raw metrics'} for v in (1, 2)]
data['completed'].append('TASK04: уточнены review/контекстные зависимости без изменения бизнес-предложения или входов')
saved = publish(data, 'task04-metadata-v1', project)
readme = (project / 'README.md').read_text(encoding='utf-8')
readme = readme.replace('**revision4 / outputs v2 / awaiting_decision**', '**revision5 / outputs v2 / awaiting_decision**')
readme = readme.replace('History1–4/previous3', 'History1–5/previous4')
readme += '\nTASK04 исправил только [метаданные зависимостей](evidence/task04-dependency-review-v1.md): экономический review C011→C013/C014 и контекст C003. Исторический README сохранён; синтетический post-decision цикл идёт в отдельной evaluation-копии и не одобряет canonical бизнес.\n'
(project / 'README.md').write_text(readme, encoding='utf-8')
assert manifest('projects/demo-002/outputs') == before_outputs
write_new(ROOT / 'evaluation/task04/canonical-metadata-result.json', {'revision_before': 4, 'revision_after': saved['revision'],
          'decision_status': saved['decision']['status'], 'outputs_unchanged': True, 'state_sha256': saved['state_sha256']})
print(json.dumps({'project': 'demo-002', 'revision': saved['revision'], 'decision': saved['decision']['status'], 'outputs': 'v2 unchanged'}, ensure_ascii=False))
