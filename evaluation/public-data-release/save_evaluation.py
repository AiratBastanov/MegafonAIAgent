"""Register the coordinator's reviewed documents with the unchanged state utility."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scripts.import_materials import register
from scripts.project_state import reference, save_state

project=ROOT/'evaluation/public-data-release/projects/uci-shoppers'
assert not (project/'state').exists(), 'Already saved: load the existing evaluation instead'
register(project,'S003','inputs/official-description-v1.md','web-excerpt',
         origin='https://archive.ics.uci.edu/dataset/468/online+shoppers+purchasing+intention+dataset',
         accessed_at='2026-11-17T09:39:20+00:00',locator='Dataset Information; Additional Variable Information; License',
         retrieval_status='current_host_read',synthetic=False,
         limitations=['Краткое изложение прочитанной страницы; не точная цитата, не HTML и не независимый источник от S001.'])
paths={p.relative_to(project).as_posix():p for p in project.rglob('*') if p.is_file()}
ids={path:f'A{i:03}' for i,path in enumerate(sorted(paths),1)}
artifacts=[reference(project,path,ids[path]) for path in sorted(paths)]
sources=[]
for sid in ('S001','S002','S003'):
    names=[name for name in paths if name.startswith(f'evidence/sources/{sid}/v1/')]
    sources.append({'id':sid,'version':1,'artifact_ids':[ids[n] for n in names],'synthetic':False})

def ev(path,locator,sid=None):
    result={'artifact_id':ids[path],'locator':locator}
    if sid:
        result.update(source_id=sid,source_version=1)
    return result

original=ev('evidence/sources/S001/v1/original.csv','rows:2-12331; Month, VisitorType, Revenue','S001')
calc=ev('evidence/calculations/independent-v1.json','overall; by_visitor; by_month_visitor')
source=ev('evidence/sources/S003/v1/original.txt','Состав и единица наблюдения; Контрольные числа','S003')
def claim(cid,kind,text,evidence,derived=()):
    return {'id':cid,'kind':kind,'text':text,'evidence':evidence,'derived_from':list(derived),'synthetic':False}
claims=[
 claim('C001','source_fact','UCI описывает 12330 сессий разных пользователей, 17 признаков и Revenue как признак покупки.',[source]),
 claim('C002','computed','1908/12330 = 15.4745% сессий с покупкой; 10422 без покупки.',[original,calc]),
 claim('C003','computed','New: 422/1694=24.9115%; Returning:1470/10551=13.9323%; Other:16/85=18.8235%.',[original,calc]),
 claim('C004','computed','Доля у новых выше в 9 из 10 представленных месяцев; исключение Feb с одним новым посетителем.',[original,calc]),
 claim('C005','hypothesis','Причины различия могут быть в намерениях, канале, товарах и сезонности; причинный эффект не установлен.',[],['C001','C003','C004']),
 claim('C006','recommendation','Предложить диагностику на современных данных до вмешательства; решение за владельцем.',[],['C002','C003','C005']),
 claim('C007','hypothesis','Объяснение условий покупки может помочь, если диагностика подтвердит соответствующий барьер.',[],['C005']),
 claim('C008','recommendation','Сообщать только проверенные условия; будущую помощь не выдавать за доступную функцию.',[],['C006','C007']),
 claim('C009','recommendation','После допуска сравнить конкретную функцию с обычным путём по случайному назначению до воздействия.',[],['C006','C007']),
 claim('C010','assumption','Предлагаются 28 дней набора, семь дней на покупку каждого пользователя и отдельное фактическое окно возвратов.',[
     ev('outputs/v1/validation-plan.md','Предлагаемое окно набора; сроки являются допущением')])]
outputs={name:ids[f'outputs/v1/{name}.md'] for name in ('situation','options','product-strategy','communication-strategy','validation-plan')}
state={'schema_version':1,'project_id':'uci-shoppers',
       'objective':'Одна изолированная проверка существующего агента на независимом публичном CSV.',
       'decision_question':'Есть ли основание менять путь покупки по типу посетителя?',
       'stage':'awaiting_decision','completed':['Проверены все строки оригинала и описание UCI','Штатный импорт без усечения',
       'Штатный расчёт и независимый пересчёт всех 23 групп','Подготовлены пять документов и критическая проверка координатора'],
       'artifacts':artifacts,'sources':sources,'claims':claims,
       'artifact_dependencies':[{'from':ids['evidence/sources/S001/v1/original.csv'],'to':ids['inputs/session-counts-v1.csv'],
                                 'reason':'Все исходные ячейки сохранены; добавлены три явно определённых поля'},
                                {'from':ids['inputs/session-counts-v1.csv'],'to':ids['evidence/calculations/by-month-visitor-v1.json'],
                                 'reason':'Штатный расчёт по версии S002/v1'}],
       'unresolved_questions':['Современные данные магазина','Причина непокупки','Маржа, расходы и допустимый риск','Владелец и разрешение диагностики'],
       'pending_actions':['Получить решение владельца о диагностике или отказе от гипотезы'],
       'next_action':'Прочитать пять результатов и решить, получать ли современные данные для диагностики; повторно не импортировать UCI.',
       'decision':{'status':'awaiting_decision','current_outputs':outputs}}
(project/'drafts').mkdir()
with (project/'drafts/checkpoint-v1.json').open('x',encoding='utf-8') as f:
    json.dump(state,f,ensure_ascii=False,indent=2)
saved=save_state(project,state)
print(json.dumps({'revision':saved['revision'],'state_sha256':saved['state_sha256'],
                  'artifacts':len(artifacts),'claims':len(claims)},ensure_ascii=False))
