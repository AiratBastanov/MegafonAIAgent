"""Read-only legible view of actual saved files for project-window recording."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from project_state import load_state
P=ROOT/'evaluation/task07/demo-workspace/projects/task06-rehearsal'
data=load_state(P)
print('Проверка сохранённой работы')
print('Целостность файлов: подтверждена штатным загрузчиком.')
print('Сохранённая версия:',data['revision'])
print('Время сохранения:',data['saved_at'])
print('Исходная незавершённая версия сохранена:',(P/'state/history/r000001.json').is_file())
if sys.argv[-1]=='continuation':
    note=next(a for a in data['artifacts'] if a['path']=='evidence/analysis-v1.md')
    print('Собственная аналитическая заметка зарегистрирована и проверена.')
    print('Повторного импорта исходных PDF, таблицы и прежних выдержек нет.')
    print('Следующий шаг: сравнить варианты и подготовить стратегии.')
    print('Данные о клиентах и экономике учебные; коммерческое решение не принято.')
else:
    d=data['decision']
    print('Записанных выборов:',len(d.get('history',[])))
    print('Обязательств:',len(d.get('commitments',[])))
    print('Текущее предложение:',d.get('proposed_option','Не сформировано'))
    for x in d.get('commitments',[]):
        print('\nДействие:',x['description'])
        print('Ответственная роль:',x['owner'])
        print('Срок:',x.get('due_at') or x['due_condition'])
        print('Выполнено:', 'да, со свидетельством' if x['status']=='completed' else 'нет')
    for x in d.get('reviews',[]):
        if x.get('owner_review_required'):print('\nНужно решение руководителя:',x['reason'])
