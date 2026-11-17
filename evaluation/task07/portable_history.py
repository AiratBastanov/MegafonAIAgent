"""Preserve raw historical Markdown and add separate portable navigation copies."""
from pathlib import Path
import hashlib,json,os,re
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[2]
out=ROOT/'submission/portable-evidence-new';out.mkdir(exist_ok=False)
sources={
 'docs/history/DEVELOPMENT_STATE-before-TASK07.md':ROOT/'docs',
 'docs/history/SUBMISSION_READINESS-before-TASK07.md':ROOT/'docs',
 'docs/history/README-before-TASK07.md':ROOT,
 **{p.relative_to(ROOT).as_posix():ROOT/'submission' for p in (ROOT/'evaluation/task07/prior-jury').glob('*.md')}
}
rows=[]
for n,(name,base) in enumerate(sources.items(),1):
    source=ROOT/name;target=out/f'{n:02d}-{source.name}';mapping=[]
    text=source.read_text(encoding='utf-8')
    def replace(m):
        raw=m[1];path,sep,fragment=raw.partition('#')
        if not path or re.match(r'^[a-zA-Z]+:',path):return m[0]
        actual=(base/unquote(path.strip('<>'))).resolve()
        assert actual.is_file(),(name,path,actual)
        actual.relative_to(ROOT)
        mapping.append({'original':unquote(path.strip('<>')),'packaged':actual.relative_to(ROOT).as_posix()})
        portable=Path(os.path.relpath(actual,target.parent)).as_posix()
        return ']('+portable+(sep+fragment if sep else '')+')'
    converted=re.sub(r'\]\(([^\n)]+)\)',replace,text)
    target.write_text('> Исторический документ. Статусы относятся ко времени его создания; актуальный итог — в материалах жюри.\n\n'+converted,encoding='utf-8')
    rows.append({'source':name,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'view':target.relative_to(ROOT).as_posix(),'mappings':mapping})
(ROOT/'evaluation/task07/portable-links.json').write_text(json.dumps({'copies':rows},ensure_ascii=False,indent=2),encoding='utf-8')
index=['# Дополнительная навигация по сохранённой истории','','Исходные документы сохранены без изменения байтов; исправлены только ссылки в отдельных копиях.','']
index += [f'- [Исторический документ {i+1}]({Path(r["view"]).name}) — `{r["source"]}`.' for i,r in enumerate(rows)]
(out/'README.md').write_text('\n'.join(index)+'\n',encoding='utf-8')
print(json.dumps({'copies':len(rows),'links':sum(len(r['mappings']) for r in rows)}))
