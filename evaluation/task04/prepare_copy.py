"""Сохранить происхождение и скопировать проверенные файлы; без нового бизнес-кейса."""
import copy
import json
from pathlib import Path
import shutil
from project_io import ROOT, PROJECT, ps, attach, publish
from observe import log

source = ROOT / 'projects/demo-002'
original = ps.load_state(source)
assert original['revision'] == 4 and original['decision']['status'] == 'awaiting_decision'
PROJECT.mkdir(parents=True, exist_ok=False)
for dirname in ('inputs', 'evidence', 'outputs'):
    shutil.copytree(source / dirname, PROJECT / dirname)
shutil.copyfile(source / 'project.md', PROJECT / 'evidence/origin-project-demo002.md')
shutil.copyfile(source / 'state/current.json', PROJECT / 'evidence/origin-state-demo002-r4.json')
(PROJECT / 'project.md').write_text('''# task04-followup — изолированная оценка сопровождения

Происхождение: canonical demo-002 revision4 / outputs v2, неизменённые исходные файлы в этой копии. Origin state закреплён отдельным артефактом. Это тот же учебный B2B-кейс TASK03, не третий новый анализ и не официальный бриф.

Все новые owner events, времена и роль владельца в этом проекте синтетические. Разрешена только локальная симуляция выбора/сопровождения/отзыва поддержки. Реальный пилот, расход, контакты и внешние сообщения не разрешены. Demo-001/demo-002 и TASK03 continuation-workspace не входят в область записи этой оценки.

Один координатор. При вызове загрузить state и knowledge/procedures/decision-followup.md из корня репозитория. Реальный interpreter — корневая .venv/Scripts/python.exe; зависимости не копируются. Project ID task04-followup; все evidence paths относительны этой папке. Сведения прежнего агента — производные, а не независимые источники.
''', encoding='utf-8')
data = copy.deepcopy(original)
data['project_id'] = PROJECT.name
data['evaluation'] = {'synthetic': True, 'origin_project_id': original['project_id'], 'origin_revision': 4,
                      'origin_state_sha256': original['state_sha256'], 'scope': 'Только локальная симуляция TASK04'}
for artifact in data['artifacts']:
    if artifact['id'] == 'PROJECT':
        artifact['path'] = 'evidence/origin-project-demo002.md'
attach(data, 'project.md', 'EVAL-PROJECT')
attach(data, 'evidence/origin-state-demo002-r4.json', 'ORIGIN-STATE')
for claim in data['claims']:
    if claim['id'] == 'C011':
        claim['review_dependencies'] = ['C013', 'C014']
    if claim['id'] in {'C006', 'C007'}:
        claim['derived_from'] = []
        claim['context_from'] = ['C003']
data['artifact_dependencies'] = [
    {'from': f'ECON-RAW-v{v}', 'to': f'ECON-v{v}', 'reason': 'Сценарии используют значения raw metrics'} for v in (1, 2)]
data['decision'].update(format_version=2, question=data['decision_question'], history=[], events=[], commitments=[],
                        metrics=[], conditions=[], reviews=[], current_outputs={name: 'OUTPUT-v2-' + name for name in
                         ['situation', 'options', 'product-strategy', 'communication-strategy', 'validation-plan']})
data['next_action'] = 'Зафиксировать синтетический выбор владельца и условия обучения/масштабирования в изолированной оценке'
log('demo_started', origin_project='demo-002', origin_revision=4, target_project=PROJECT.name,
    observation='Координатор начинает фактический workflow; часы условий далее явно simulated')
saved = publish(data, 'initial-v1')
print(json.dumps({'project': str(PROJECT.relative_to(ROOT)), 'revision': saved['revision'], 'origin_revision': 4}, ensure_ascii=False))
