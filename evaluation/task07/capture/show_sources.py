"""Read-only, locator-preserving display of already registered source extracts."""
from pathlib import Path
import argparse
import json
from show_economics import ROOT,only,load_state,scoped_path

def read_registered(project,state,source_id,version,suffix):
    source=only(state['sources'],lambda s:s['id']==source_id and s['version']==version)
    artifact=only(state['artifacts'],lambda a:a['id'] in source['artifact_ids'] and a['path'].endswith(suffix))
    return json.loads(scoped_path(project,artifact['path']).read_text(encoding='utf-8'))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('kind',choices=['pdf','xlsx','yandex'])
    parser.add_argument('--project',default='evaluation/task07/demo-workspace/projects/task06-rehearsal')
    args=parser.parse_args();project=(ROOT/args.project).resolve();project.relative_to(ROOT)
    state=load_state(project)
    print('Просмотр сохранённых источников после продолжения.\n')
    print('Целостность файлов проверена штатным загрузчиком; повторного импорта нет.\n')
    if args.kind=='pdf':
        data=read_registered(project,state,'S001',1,'/extract.json')
        if data.get('synthetic') is not True:raise ValueError('Ожидался учебный PDF')
        page=only(data['pages'],lambda p:p['physical_page']==2)
        print('Учебный PDF — физическая страница 2, блоки 2–4.\n')
        for n in [2,3,4]:
            block=only(page['blocks'],lambda b:b['locator']==f'physical-page:2/block:{n}')
            print(f'Блок {n}: '+block['text']+'\n')
        print('Русское пояснение к английскому исходнику:')
        print('«Платный пилот» здесь означает интерес к платному предложению.')
        print('Поступления не сверяли; показатель первой оплаты требует полученных денег.')
        print('Это учебный документ, а не сведения о реальных клиентах.')
    elif args.kind=='xlsx':
        data=read_registered(project,state,'S002',1,'/extract.json')
        if data.get('synthetic') is not True:raise ValueError('Ожидалась учебная таблица')
        sheet=only(data['sheets'],lambda s:s['name']=='Воронка')
        cells={c['address']:c for c in sheet['cells']}
        print('Учебная таблица, лист «Воронка», выбранные ячейки D3:F4.\n')
        for row in [3,4]:
            print('Сегмент: '+str(cells[f'B{row}']['value']))
            for col,label in [('D','Начали пробу'),('E','Проявили интерес'),('F','Первая оплата')]:
                cell=cells[f'{col}{row}'];print(f'{cell["locator"]:<20} {label:<22} {cell["value"]}')
            missing=cells[f'I{row}']['value']
            print(f'Затраты привлечения, I{row}: '+('неизвестны' if missing is None else str(missing)))
            print()
        print('Показаны исходные значения. Интерес и оплата — разные столбцы.')
        print('Ни отсутствие расходов, ни рыночный спрос из этих ячеек не следуют.')
    else:
        expected='https://yandex.ru/support/yandex-360/customers/disk/web/ru/share/sharing'
        candidates=[]
        for source in state['sources']:
            meta=read_registered(project,state,source['id'],source['version'],'/source.json')
            if meta.get('origin')==expected:candidates.append((source,meta))
        if not candidates:raise ValueError('Снимок официальной справки не зарегистрирован')
        source,meta=max(candidates,key=lambda pair:pair[0]['version'])
        data=read_registered(project,state,source['id'],source['version'],'/extract.json')
        print('Официальная справка Яндекс Диска; датированный пересказ.')
        for n in [2,3,7,11]:
            line=only(data['lines'],lambda v:v['locator']==f'line:{n}')
            print(line['text'])
            if n==3:print()
            if n==7:
                print('Пояснение: «только просмотр» исключает редактирование.')
                print('Пароль сам по себе не означает запрета скачивания: это отдельная настройка.')
                print()
        print('Координата: «Как поделиться», строки 86–114 исходной страницы.')
        print('Это просмотр зарегистрированного снимка, а не новое обращение к сайту.')
