"""Последняя запись координатора: только проверенные уже созданные артефакты."""
from datetime import datetime, timezone
import json
import shutil
from project_io import ROOT, PROJECT, ps, attach, publish
from observe import log

data = ps.load_state(PROJECT)
assert data['revision'] == 10
shutil.copyfile(ROOT / 'evaluation/task04/independent-review-v2.md', PROJECT / 'evidence/independent-review-task04-v1.md')
attach(data, 'evidence/independent-review-task04-v1.md', 'INDEPENDENT-REVIEW-TASK04')
attach(data, 'evidence/nonmaterial-check-v1.json', 'NONMATERIAL-CHECK')
shutil.copyfile(ROOT / 'evaluation/task04/actions.jsonl', PROJECT / 'evidence/actions-snapshot-task04-v1.jsonl')
attach(data, 'evidence/actions-snapshot-task04-v1.jsonl', 'TASK04-ACTIONS-SNAPSHOT')
data['completed'].extend([
    'TASK04: реально выполненный текущим host-координатором локальный синтетический lifecycle; без рыночного исполнения',
    'Отзыв поддержки согласован в пяти outputs/v3; выбор и его basis сохранены',
    'Числовая ветка и nonmaterial/replay проверены; S002@1 funnel и ECON-v2 переиспользованы',
    'Независимое автоматическое review и focused fixes выполнены; human acceptance не получено',
])
data['pending_actions'] = [
    'Учебному владельцу решить вопрос пересмотра WITHDRAW-01; предложение C016 не принято автоматически',
    'Получить протокол фактической возможности и назначить владельца цены информации',
    'Не считать полные simulated окна фактическими данными; частота/ценность/продления/полные расходы неизвестны',
]
start = json.loads((ROOT / 'evaluation/task04/observations/demo-prepare/result.json').read_text(encoding='utf-8'))['started_at']
data['resources']['demonstration_started_at'] = start
data['resources']['final_artifacts_prepared_at'] = datetime.now(timezone.utc).isoformat()
data['resources']['measurement_note'] = 'Demo вложен в development; начало из observed demo-prepare, конец фиксирует отдельная приёмка после load. Не суммировать интервалы.'
saved = publish(data, 'final-followup-v1')
log('demo_state_ready_for_separate_load', project_id=PROJECT.name, revision=saved['revision'],
    history_count=len(saved['decision']['history']), commitments=len(saved['decision']['commitments']),
    owner_review_active=True, real_business_approval=False)
print(json.dumps({'revision': saved['revision'], 'state_sha256': saved['state_sha256'], 'next_action': saved['next_action']}, ensure_ascii=False))
