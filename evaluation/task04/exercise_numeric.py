"""Сопоставление существующей коррекции; расчёт проверки, не новая стратегия."""
from decimal import Decimal
import json
from project_io import PROJECT, ps, df, attach, publish
from observe import write_new, log

data = ps.load_state(PROJECT)
assert data['revision'] == 7
event = dict(id='ECON-RECHECK-01', project_id=PROJECT.name, kind='evidence_change', at='2026-11-19T10:00:00+03:00', clock='simulated',
             provenance={'kind': 'source_material', 'artifact_id': 'S005v1-extract', 'locator': 'line:1-5'},
             change=dict(type='changed_assumption', source={'id': 'S002', 'version': 1}, replacement={'id': 'S002', 'version': 2},
                         locators=["'Экономика'!E3"], reason='Проверить достижимость экономического условия по существующей коррекции поддержки 30→90 минут',
                         old_ground='S002@1: поддержка 30 минут, вклад 2100, N20 остаток 12000',
                         new_ground='S002@2: 90 минут, вклад 1500, N20 остаток 0 до неизвестных расходов',
                         applicability='Повторная проверка объявленных зависимостей уже принятого сценария v2; не новый рыночный факт и не переимпорт'))
write_new(PROJECT / 'inputs/economic-event-v1.json', event)
report = df.impact(PROJECT, data, event)
assert len(report['comparison']['changes']) == 1
assert report['comparison']['changes'][0]['locator'] == "'Экономика'!E3"
affected = {x['node'] for x in report['affected']}
assert {'claim:C013', 'claim:C011', 'condition:G-ECONOMICS'} <= affected
assert 'claim:C007' not in affected
assert any(x['artifact_id'] == 'CALC-FUNNEL-v1' for x in report['reusable'])
old = df.xlsx_extract(PROJECT, data, {'id': 'S002', 'version': 1})
new = df.xlsx_extract(PROJECT, data, {'id': 'S002', 'version': 2})
values = {}
for version, extracted in [(1, old), (2, new)]:
    cells = {c['locator']: c for sheet in extracted['sheets'] for c in sheet['cells']}
    selected = {letter: Decimal(str(cells[f"'Экономика'!{letter}3"]['value'])) for letter in 'CDEFGHI'}
    margin = selected['C'] - selected['D'] - selected['E'] * selected['F'] / Decimal(60)
    surplus = selected['I'] * margin - selected['G']
    calc = json.loads((PROJECT / f'evidence/calculations/economics-v{version}.json').read_text(encoding='utf-8'))
    assert Decimal(calc['base']['margin_rub_per_account_month']) == margin
    assert Decimal(calc['base']['surplus_before_unknown_costs_rub_month']) == surplus
    values[str(version)] = {'source': f'S002@{version}', 'locator': "'Экономика'!C3:I3", 'input_values': {k: str(v) for k, v in selected.items()},
                            'margin': str(margin), 'surplus_N20': str(surplus), 'unknown_costs': None,
                            'unit': 'RUB/платящую организацию/месяц; остаток RUB/месяц', 'checked_against': f'ECON-v{version}/base'}
check = {'synthetic': True, 'method': 'Decimal из закреплённых literal cells; сверка уже существующих ECON-v1/v2',
         'values': values, 'recomputed_production_artifacts': [], 'reuse': 'CALC-FUNNEL-v1 и ECON-v2 уже соответствуют выбранным входам; новые расчётные версии не нужны',
         'changes': report['comparison']['changes'], 'passed': True}
write_new(PROJECT / 'evidence/economic-impact-v1.json', report)
write_new(PROJECT / 'evidence/economic-recheck-v1.json', check)
attach(data, 'evidence/economic-impact-v1.json', 'ECON-IMPACT')
attach(data, 'evidence/economic-recheck-v1.json', 'ECON-RECHECK')
data, changed = df.apply_event(PROJECT, data, event)
assert changed
saved = publish(data, 'economic-review-pending-v1')
log('numeric_dependency_observed', project_id=PROJECT.name, revision=saved['revision'], funnel_reused=True,
    changed_cell="'Экономика'!E3", old_minutes=30, new_minutes=90, actual_market_observation=False)
print(json.dumps({'revision': saved['revision'], 'decisive_paths': [a for a in report['affected'] if a['node'] in {'claim:C013', 'claim:C011', 'condition:G-ECONOMICS'}],
                  'funnel_affected': False, 'values': values}, ensure_ascii=False, indent=2))
