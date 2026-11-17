"""Read-only view of already registered calculations; no new arithmetic or state writes."""
from pathlib import Path
import argparse
import json
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
WORKSPACE=ROOT/'evaluation/task07/demo-workspace'
sys.path.insert(0,str(WORKSPACE/'scripts'))
from project_state import load_state,scoped_path

def only(items,predicate):
    selected=[item for item in items if predicate(item)]
    if len(selected)!=1:raise ValueError('Неоднозначная или отсутствующая запись расчёта')
    return selected[0]

def number(value):
    if value is None:return 'неизвестно'
    whole,_,fraction=str(value).partition('.')
    rendered=f'{int(whole):,}'.replace(',',' ')
    if fraction.strip('0'):rendered+=','+fraction
    return rendered

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--project',default='evaluation/task07/demo-workspace/projects/task06-rehearsal')
    args=parser.parse_args();project=(ROOT/args.project).resolve();project.relative_to(ROOT)
    state=load_state(project)
    artifact=only(state['artifacts'],lambda a:a['id']=='ANALYSIS_CALC')
    calculation=json.loads(scoped_path(project,artifact['path']).read_text(encoding='utf-8'))
    if calculation.get('synthetic') is not True:
        raise ValueError('Ожидался явно учебный расчёт; происхождение необходимо проверить')
    scenarios=calculation['economics_scenarios']
    low=only(scenarios,lambda s:s['support_minutes']=='30')
    high=only(scenarios,lambda s:s['support_minutes']=='90')
    low20=only(low['balances'],lambda b:b['accounts']=='20')
    high20=only(high['balances'],lambda b:b['accounts']=='20')
    print('Учебные допущения — не продажи и не прибыль.\n')
    print('Хеши состояния, источников и расчётов проверены штатным загрузчиком.')
    print('Ни импорта, ни нового расчёта: читаем сохранённую чувствительность.\n')
    print(f'{"Показатель":<48}{"30 минут":>12}{"90 минут":>12}')
    print(f'{"Поддержка: ₽ на организацию в месяц":<48}{number(low["support_cost_rub"]):>12}{number(high["support_cost_rub"]):>12}')
    print(f'{"Вклад: ₽ на организацию в месяц":<48}{number(low["unit_contribution_rub"]):>12}{number(high["unit_contribution_rub"]):>12}')
    print(f'{"Организаций для покрытия указанных расходов":<48}{number(low["fixed_coverage_accounts"]):>12}{number(high["fixed_coverage_accounts"]):>12}')
    print(f'{"Остаток при 20 организациях: ₽ в месяц":<48}{number(low20["monthly_balance_rub"]):>12}{number(high20["monthly_balance_rub"]):>12}')
    print('\nЭто сравнение сценариев, а не сообщение о новом наблюдении.')
    print('Привлечение, налоги, продления и стоимость выхода остаются неизвестными.')
    print('Нулевой остаток не покрывает разовую подготовку.')
