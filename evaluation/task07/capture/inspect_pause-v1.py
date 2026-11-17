"""Display actual saved checkpoint fields for the capture, without editing it."""
from pathlib import Path
import json
import hashlib

p=Path('evaluation/task07/demo-workspace/projects/task06-rehearsal/state/current.json')
d=json.loads(p.read_text(encoding='utf-8'))
print('Читаем подлинную сохранённую версию из отдельной копии.\n')
for k,label in [('revision','Сохранённая версия'),('stage','Этап'),('saved_at','Время сохранения'),('updated_at','Время обновления'),('next_action','Следующий шаг')]:
    if k in d:print(label+': '+str(d[k])+'\n')
for k,label in [('calculations','Расчёты'),('outputs','Готовые стратегии')]:
    print(label+': '+str(len(d.get(k,[]))))
print('\nКонтрольная сумма файла: '+hashlib.sha256(p.read_bytes()).hexdigest())
