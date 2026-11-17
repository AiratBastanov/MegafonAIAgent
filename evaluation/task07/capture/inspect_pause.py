"""Display actual saved checkpoint fields for the capture, without editing it."""
from pathlib import Path
import json
import hashlib

p=Path('evaluation/task07/demo-workspace/projects/task06-rehearsal/state/current.json')
d=json.loads(p.read_text(encoding='utf-8'))
if d['revision'] != 1:
    raise SystemExit('Эта копия уже продолжена. Прежнюю паузу нельзя выдавать за текущую версию.')
print('Читаем подлинную сохранённую версию из отдельной копии.\n')
for k,label in [('revision','Сохранённая версия'),('stage','Этап'),('saved_at','Время сохранения'),('updated_at','Время обновления'),('next_action','Следующий шаг')]:
    if k in d:print(label+': '+str(d[k])+'\n')
paths=[a['path'] for a in d['artifacts']]
print('Зарегистрированные расчёты: '+str(sum(p.startswith('evidence/calculations/') for p in paths)))
print('Готовые стратегии: '+str(sum(p.startswith('outputs/') for p in paths)))
print('\nКонтрольная сумма файла: '+hashlib.sha256(p.read_bytes()).hexdigest())
