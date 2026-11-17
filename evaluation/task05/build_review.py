"""Собрать пакет автоматическому reviewer без labels A/B и без оценок координатора."""
from pathlib import Path
import json
import re
import shutil
from datetime import datetime, timezone

BASE=Path(__file__).resolve().parent


def main():
    out=BASE/'review-input'
    out.mkdir(exist_ok=False)
    shutil.copytree(BASE/'frozen-v2/B/materials',out/'primary/materials')
    shutil.copyfile(BASE/'frozen-v2/B/context.md',out/'primary/context.md')
    shutil.copytree(BASE/'frozen-v2/events',out/'primary/events')
    for filename in ('rubric-v1.json','expectations-v1.json'):
        shutil.copyfile(BASE/filename,out/filename)
    aliases={'A':'R17','B-ablation':'R42'}
    # Порядок проверяется повторной оценкой при его обмене; randomness не заявляется.
    order={'q1':['B-ablation','A'],'q2':['A','B-ablation'],'q3':['B-ablation','A']}
    lines=['# Полные тексты для независимого review', '',
        'Оцените только пользовательский исход. Происхождение/модель не раскрываются, но стиль и файловые ссылки могут выдать конфигурацию.',
        'Первичные файлы: primary/context.md, primary/materials и primary/events. Ссылки ниже нормализованы только для сокрытия workspace; содержание ответов не сокращено.', '']
    for q in ('q1','q2','q3'):
        request=(BASE/'frozen-v2/prompts/B'/(q+'.txt')).read_text(encoding='utf-8')
        start={'q1':'В обеих ветках на','q2':'Продолжи обе ветки на','q3':'На 2026-12-19T14'}[q]
        request=request[request.index(start):].split('\n\nПрочитай RUNTIME.md.')[0]
        lines += ['## '+q,request,'']
        for condition in order[q]:
            alias=aliases[condition]
            text=(BASE/'runs'/condition/q/(q+'.md')).read_text(encoding='utf-8')
            text=re.sub(r'C:[/\\]Users[/\\]BastaPC[/\\]AppData[/\\]Local[/\\]Temp[/\\]megafon-task05-clean-20zjuuxd[/\\][AB]',alias,text)
            lines += ['### '+alias,text,'']
    (out/'responses.md').write_text('\n'.join(lines),encoding='utf-8')
    # Реальные новые документы для проверки утверждений о handoff/completion.
    for condition,alias in aliases.items():
        name='A' if condition=='A' else 'B'
        workspace=BASE/'collected'/name
        initial=json.loads((BASE/'freeze-manifest-v2.json').read_text(encoding='utf-8'))['files']
        for p in workspace.rglob('*'):
            if not p.is_file() or '__pycache__' in p.parts:
                continue
            rel=p.relative_to(workspace)
            if any(t in rel.parts for t in ('logs','responses')) or p.suffix not in {'.md','.json'}:
                continue
            if 'frozen-v2/'+name+'/'+rel.as_posix() in initial:
                continue
            # State/meta can directly expose identity; notes and analytical amendments suffice.
            if 'state' in rel.parts or 'drafts' in rel.parts or 'meta' in p.name:
                continue
            if not any(t in rel.parts for t in ('notes','outputs')):
                continue
            dest=out/alias/rel
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(p,dest)
    (BASE/'review-blinding-map.json').write_text(json.dumps({'created_at':datetime.now(timezone.utc).isoformat(),
        'aliases':aliases,'order':order,'limits':'процедурное ослепление, структура/стиль раскрывают конфигурацию; shared model неизвестна; human calibration нет'},ensure_ascii=False,indent=2),encoding='utf-8')
    print(str(out))


if __name__=='__main__':
    main()
