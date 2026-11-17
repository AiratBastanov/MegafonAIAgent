"""Закрепить написанные host-координатором тексты и их явные основания."""
import json
from project_io import PROJECT, ps, df, attach, publish
from observe import log

data = ps.load_state(PROJECT)
assert data['revision'] == 6
attach(data, 'evidence/withdrawal-impact-v1.json', 'WITHDRAWAL-IMPACT')
attach(data, 'evidence/withdrawal-review-v1.md', 'WITHDRAWAL-REVIEW')
for name in data['decision']['current_outputs']:
    aid = 'OUTPUT-v3-' + name
    attach(data, 'outputs/v3/' + name + '.md', aid)
    data['decision']['current_outputs'][name] = aid
data['claims'] += [
    dict(id='C015', kind='source_fact', synthetic=True, derived_from=[],
         text='Синтетический S006 отзывает поддержку безаккаунтного доступа получателя из S001@1/block5; это не доказательство обязательного аккаунта и не реальная приёмка',
         evidence=[{'artifact_id': 'S006v1-extract', 'locator': 'line:2-3', 'source_id': 'S006', 'source_version': 1}]),
    dict(id='C018', kind='hypothesis', synthetic=True, derived_from=['C004', 'C007', 'C015'],
         text='Ручная помощь может снижать координацию относительно обычного инструмента; способность предложенного пакета, частота задач и денежная ценность ещё неизвестны',
         evidence=[{'artifact_id': 'S001v1-extract', 'locator': 'physical-page:2/block:5-6', 'source_id': 'S001', 'source_version': 1}]),
    dict(id='C016', kind='recommendation', synthetic=True, derived_from=['C015', 'C018', 'C013', 'C005', 'C006'],
         review_dependencies=['C013', 'C014'], status='proposed',
         text='Предложить владельцу сохранить внутренний режим, снять неподтверждённое обещание и сначала решить, оправданы ли приёмка возможности и цена информации; не подменять исторический выбор новым одобрением', evidence=[]),
    dict(id='C017', kind='assumption', synthetic=True, derived_from=['C016'], context_from=['C012'],
         text='Learning gates времени/доставки/первой оплаты не обосновывают цену или масштабирование; отдельно нужны фактическая частота, ценность, продления и полные затраты, все правила пока предложены',
         evidence=[{'artifact_id': 'FOLLOWUP-PROTOCOL', 'locator': 'абзацы 2–5'}]),
]
for condition in data['decision']['conditions']:
    condition['output_ids'] = [aid.replace('OUTPUT-v2-', 'OUTPUT-v3-') for aid in condition['output_ids']]
    if condition['id'] == 'G-CAPABILITY':
        condition['claim_ids'] = ['C001', 'C015', 'C016']
        condition['unresolved_reason'] = 'Поддержка безаккаунтного доступа отозвана; фактический способ доступа не принят'
    if condition['id'] == 'G-ECONOMICS':
        condition['claim_ids'] = ['C008', 'C013', 'C014', 'C011', 'C016']
    if condition['id'] == 'G-VALUE':
        condition['claim_ids'] = ['C018', 'C017']
event = dict(id='REVIEW-WITHDRAW-01', project_id=PROJECT.name, kind='review', clock='simulated', at='2026-11-18T14:00:00+03:00',
             provenance={'kind': 'agent_review', 'artifact_id': 'WITHDRAWAL-REVIEW', 'locator': 'весь документ'}, review_id='review-WITHDRAW-01',
             resolution=dict(status='revised', reason='Снято неподтверждённое обещание; продукт, сообщение и проверка согласованы, история выбора сохранена',
                             owner_review_required=True,
                             next_action='Владельцу симуляции решить: вернуться к приёмке возможности и назначить ответственного за цену информации либо сохранить внутренний режим',
                             resolution_evidence=[{'artifact_id': 'WITHDRAWAL-REVIEW', 'locator': 'весь документ'},
                                                  {'artifact_id': 'OUTPUT-v3-communication-strategy', 'locator': 'Текущее сообщение; фраза снята'}],
                             proposed_option='Сохранить внутренний режим; сначала решить вопрос приёмки доступа получателя и цены информации. Предложение пересмотра C016 ожидает владельца'))
data, _ = df.apply_event(PROJECT, data, event)
data['next_action'] = event['resolution']['next_action']
data['stage'] = 'decision_review_required'
saved = publish(data, 'withdrawal-reviewed-v1')
log('host_analysis', project_id=PROJECT.name, revision=saved['revision'],
    observation='Написаны пять v3 outputs; числовые артефакты сохранены. Аналитический review revised, выбор владельца не заменён.')
print(json.dumps({'revision': saved['revision'], 'status': saved['decision']['status'], 'review': 'revised', 'owner_review_required': True}, ensure_ascii=False))
