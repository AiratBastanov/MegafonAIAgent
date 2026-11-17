"""Одноразовая сборка финального draft/журнала TASK03, без записи current state."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from scripts.project_state import load_state, reference, validate_state
from scripts.import_materials import write_new, json_bytes

p = REPO / 'projects/demo-002'
s = load_state(p)
assert s['revision'] == 3 and s['decision']['status'] == 'awaiting_decision'
recorded = datetime.now(timezone.utc).isoformat()
for version in (1, 2):
    original = REPO / f'evaluation/task03/demo002-review-v{version}.md'
    body = original.read_text(encoding='utf-8')
    body = body.replace('../../projects/demo-002/', '../')
    body = body.replace('[manifest](demo001-baseline-manifest.json)', '`evaluation/task03/demo001-baseline-manifest.json`')
    body = body.replace('(demo001-baseline-manifest.json)', '(../../../evaluation/task03/demo001-baseline-manifest.json)')
    header = (f'> Копия автоматического обзора; исправлены только относительные ссылки для расположения в проекте. '
              f'Оригинал: `evaluation/task03/{original.name}`; SHA-256 оригинальных байт: '
              f'`{hashlib.sha256(original.read_bytes()).hexdigest()}`. Не первичный источник рыночных фактов.\n\n')
    write_new(p / f'evidence/{original.name}', (header + body).encode('utf-8'))

events = [
    ('2026-11-16T09:30:57+00:00', 'start', 'Учебный менеджерский запрос; вопросы выбраны координатором', []),
    ('2026-11-16T09:34:45+00:00', 'import_and_verify', 'PDF/XLSX и host-read web выдержки; fidelity39 PASS', ['S001@1','S002@1','S003@1','S004@1']),
    ('2026-11-16T09:37:07.569335+00:00', 'save_checkpoint', 'Незавершённая revision1 до конфликта и outputs', ['S001@1','S002@1','S003@1','S004@1']),
    ('2026-11-16T09:47:33.790236+00:00', 'fresh_cli_ended', 'Один процесс, транспорт TLS/reset/HTTP403; новой работы/state нет; separate load revision1; NOT_VERIFIED', ['S001@1','S002@1']),
    ('2026-11-16T10:04:21.941754+00:00', 'root_phase_save', 'Координатор разрешил конфликт, вычислил показатели и написал пять outputs/v1; revision2', ['S001@1','S002@1','S003@1','S004@1']),
    ('2026-11-16T10:05:17+00:00', 'correction', 'Синтетическое E3 30→90; Воронка не менялась', ['S002@2','S005@1']),
    ('2026-11-16T10:09:35.015352+00:00', 'corrected_save', 'Пересчитана экономика; исправлены окна и знаменатели; revision3/outputs v2', ['S002@2','S005@1']),
    (recorded, 'review_attached', 'Независимое автоматическое v2 review PASS; R3 исправлен в draft, не business approval', ['S002@2','S005@1']),
]
lines = ''.join(json.dumps({'observed_at':t,'recorded_at':recorded,'recording':'retrospective_from_logs_and_state',
                          'action':a,'outcome':o,'input_versions':v,'tokens':None,'charges':None},ensure_ascii=False)+'\n'
                for t,a,o,v in events).encode('utf-8')
write_new(p/'state/actions.jsonl', lines)
write_new(p/'evidence/actions-snapshot-v1.jsonl', lines)
for aid, path in [
    ('REVIEW-v1','evidence/demo002-review-v1.md'), ('REVIEW-v2','evidence/demo002-review-v2.md'),
    ('RUN-OBSERVATION-v2','evidence/run-observation-v2.md'), ('ACTIONS-v1','evidence/actions-snapshot-v1.jsonl')
]:
    s['artifacts'].append(reference(p, path, aid))
next(c for c in s['claims'] if c['id']=='C003')['text'] = ('В учебной книге раздельно заданы contacted, trials, interest и paid30, '
    'имеются неизвестные расходы и формулы без проверенного кэша; это описание исходных полей, не подтверждение спроса или свежести кэша')
s['completed'].extend(['Независимое автоматическое ревью outputs/v2 завершено: существенные замечания закрыты',
                       'C003 уточнён после R3, завершённые шаги убраны из очереди, обзоры и журнал закреплены'])
s['pending_actions'] = ['Уполномоченный владелец должен рассмотреть outputs/v2, назначить ответственного и решить вопрос бюджета проверки',
                        'До пилота получить фактические затраты, проверить возможности прототипа и пригодность/согласие будущих участников',
                        'Сопоставить с официальным дополнительным брифом, когда его удастся прочитать разрешённым маршрутом']
s['next_action'] = ('Передать владельцу текущие пять outputs/v2 для решения о цене информации: подтвердить реальные затраты, '
                    'приёмку возможностей и бюджет; без его решения не запускать пилот, контакты или новую разработку. '
                    'При новых материалах сначала проверить применимость и зарегистрировать только изменившиеся источники.')
s['continuation_phase'] = {'bounded':True,'completed_by':'root coordinator; fresh CLI verification NOT_VERIFIED',
                          'completed_phase':'Конфликт, расчёты, пять стратегий, коррекция и независимое автоматическое ревью',
                          'next_phase':'Ожидание фактических данных и решения владельца; при их поступлении анализ изменения',
                          'stop_after':'Публикация финального proposed пакета и отдельный load; бизнес-решение не выдумывать'}
s['limitations'].append('Сильная проверка нового host phase/save/reload NOT_VERIFIED: транспорт прервался до нового артефакта/state')
s['resources']['final_package_prepared_at'] = recorded
s['resources']['interval_note'] = 'Конец демонстрации — saved_at финальной ревизии; общий elapsed включает ожидания/прерывание, не активное время'
for key in ('revision','saved_at','state_sha256'):
    s.pop(key, None)
validate_state(p, s)
write_new(p/'drafts/final-v2.json', json_bytes(s))
print(json.dumps({'draft':'drafts/final-v2.json','artifacts':len(s['artifacts']),'claims':len(s['claims']),'validated':True}))
