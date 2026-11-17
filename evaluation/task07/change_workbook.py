"""Materialize an explicitly instructed simulated cell change, import and calculate."""
from pathlib import Path
import json,sys,hashlib
ROOT=Path(__file__).resolve().parents[2]
WS=ROOT/'evaluation/task07/demo-workspace';P=WS/'projects/task06-rehearsal'
sys.path.insert(0,str(WS/'scripts'));sys.path.insert(0,str(ROOT/'evaluation'))
from project_state import load_state
from import_materials import register
from analyze_table import run as table
from calc_offer_scenarios import run as scenarios
from openpyxl import load_workbook
from fractions import Fraction

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    state=load_state(P);assert state['decision']['status']=='simulated_accepted'
    assert state['decision']['history']
    old=P/'inputs/offer-v1.xlsx';new=P/'inputs/offer-v2.xlsx';assert not new.exists()
    before=hashlib.sha256(old.read_bytes()).hexdigest()
    w=load_workbook(old);assert w['Экономика']['E3'].value==30
    w['Экономика']['E3']=90;w.save(new);w.close()
    a,b=load_workbook(old),load_workbook(new)
    changed=[]
    for sa in a:
        sb=b[sa.title]
        for row in sa:
            for c in row:
                if c.value!=sb[c.coordinate].value:changed.append((sa.title,c.coordinate,c.value,sb[c.coordinate].value))
    a.close();b.close();assert changed==[('Экономика','E3',30,90)]
    assert hashlib.sha256(old.read_bytes()).hexdigest()==before
    registered=register(project=P,source_id='S002',input_path='inputs/offer-v2.xlsx',kind='xlsx',synthetic=True,
        origin='Учебная коррекция по inputs/support-change-simulated-v1.md',selection_path='inputs/selection-v1.json')
    assert registered['source']['version']==2 and not registered['reused']
    raw='evidence/calculations/economics-base-v2.json'
    table(project=P,input_path='inputs/offer-v2.xlsx',spec_path='inputs/metrics-economics-v1.json',output=raw,source_id='S002',source_version=2)
    result=scenarios(P,raw,'inputs/economics-sensitivity-v1.json','evidence/calculations/support90-v1.json')
    base=result['base']
    assert Fraction(base['support_rub_per_account_month'])==900
    assert Fraction(base['margin_rub_per_account_month'])==1500
    assert Fraction(base['surplus_before_unknown_costs_rub_month'])==0
    assert base['min_accounts_nonnegative']==20 and base['min_accounts_positive']==21
    assert base['conditional_setup_payback_months'] is None
    proof={'changed_cells':changed,'original_sha256':before,'new_sha256':hashlib.sha256(new.read_bytes()).hexdigest(),
           'calculation_base':base,'independent_fraction_checks':'passed','source_version':2,'synthetic':True}
    (P/'evidence/support-change-check-v1.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Смоделированное изменение: поддержка 30 → 90 минут.')
    print('В новой таблице изменена ровно одна ячейка; исходная книга сохранена.')
    print('Новая версия источника зарегистрирована; воронка не импортировалась повторно.')
    print('\nПоддержка: 900 ₽. Вклад на организацию: 1 500 ₽ в месяц.')
    print('При 20 организациях остаток: 0 ₽ до неизвестных расходов.')
    print('Ненулевой положительный остаток начинается с 21 организации.')
    print('Возврат затрат подготовки при нулевом остатке не достигается.')
    print('\nАрифметика отдельно сверена точными дробями. Это сценарий, не наблюдение.')
