"""Read-only verification and literal excerpts of the actual final analysis."""
import json
from fractions import Fraction
from show_economics import ROOT,load_state,scoped_path,only

p=ROOT/'evaluation/task07/demo-workspace/projects/task06-rehearsal'
d=load_state(p);before=json.loads((p/'state/history/r000007.json').read_text(encoding='utf-8'))
assert d['decision']['history']==before['decision']['history']
old={a['id']:a for a in before['artifacts']};now={a['id']:a for a in d['artifacts']}
assert old['FUNNEL_CALC']==now['FUNNEL_CALC']
assert all(c['status'] in ['pending','blocked'] and not c['completion_evidence'] for c in d['decision']['commitments'])
assert len(d['decision']['current_outputs'])==5
print('Проверены история выбора, пять документов и незавершённые обязательства.\n')
ref=now[d['decision']['current_outputs']['product-strategy']]
text=scoped_path(p,ref['path']).read_text(encoding='utf-8')
paragraph=next(x for x in text.split('\n\n') if x.startswith('Сильнейшее возражение'))
print(paragraph+'\n')
plan=next(c for c in d['claims'] if c['id']=='C025')
print('Сохранённые условия проверки:')
print(plan['text'].replace('12 организаций, четыре задачи','12 организаций, четыре задачи'))
print('\nЭто предложенный план. Наблюдения клиентов и платежи не выполнялись.')
