"""Generate navigation copies for historical Markdown with stale relative links.

Raw historical files are never edited. Resolution is explicit and checked on disk.
"""
import hashlib
import json
import os
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
old=json.loads((ROOT/'evaluation/task06/packaging-prep1.json').read_text(encoding='utf-8'))['broken_markdown_links']
out=ROOT/'submission/portable-evidence';out.mkdir(parents=True,exist_ok=True)
sources=sorted({x['file'] for x in old if not x['file'].startswith(('README.md','CONTENTS.md'))})
records=[];unresolved=[]

def resolve(source,link):
    local=(source.parent/link).resolve()
    if local.is_relative_to(ROOT) and local.exists():return local
    rel=source.relative_to(ROOT).as_posix();candidates=[]
    if rel.startswith('docs/history/'):
        base=ROOT if source.name.startswith('README') else ROOT/'docs'
        candidates.append((base/link).resolve())
    if 'continuation-workspace' in rel and link.startswith('docs/'):
        candidates.append(ROOT/link)
    if source.name=='readme-before-task04.md':candidates.append((ROOT/'projects/demo-002'/link).resolve())
    if 'demo002-review-' in source.name:
        candidates.extend([(ROOT/'projects/demo-002/evidence'/link).resolve(),ROOT/'evaluation/task03/demo001-baseline-manifest.json'])
    if rel.startswith('evaluation/task05/runs/B-ablation/') or rel=='evaluation/task05/review-input/responses.md':
        if link.startswith('../'):candidates.append((ROOT/'evaluation/task05/collected/B/responses'/link).resolve())
        elif link.startswith('R17/'):candidates.append(ROOT/'evaluation/task05/collected/A'/link[4:])
        elif link.startswith('R42/'):candidates.append(ROOT/'evaluation/task05/collected/B'/link[4:])
    for p in candidates:
        if p.is_relative_to(ROOT) and p.is_file():return p
    return None

for n,relative in enumerate(sources,1):
    source=ROOT/relative
    target=out/f'{n:02}-{source.stem}.md'
    if target.exists():raise FileExistsError(target)
    mappings=[]
    def replace(match):
        raw=match.group(1);url=raw.strip('<>');link,sep,anchor=url.partition('#')
        if not link or re.match(r'^[a-zA-Z]+:',link):return match.group(0)
        found=resolve(source,link)
        if found is None:
            unresolved.append({'file':relative,'target':link});return match.group(0)
        resolved=found.relative_to(ROOT).as_posix()
        mappings.append({'original':link,'packaged':resolved})
        return ']('+os.path.relpath(found,target.parent).replace('\\','/')+(sep+anchor if sep else '')+')'
    raw=source.read_text(encoding='utf-8')
    # Preserve fenced code as raw historical content, including example paths.
    parts=re.split(r'(```.*?```)',raw,flags=re.S)
    text=''.join(part if part.startswith('```') else re.sub(r'\]\(([^\n)]+)\)',replace,part) for part in parts)
    header=f'# Навигационная копия исторического документа\n\nИсточник: `{relative}`. Исходные байты сохранены; здесь изменены только относительные Markdown-ссылки. Это не новый run или новое доказательство.\n\n'
    target.write_text(header+text,encoding='utf-8')
    records.append({'source':relative,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                    'view':target.relative_to(ROOT).as_posix(),'mappings':mappings})
result={'copies':records,'unresolved':unresolved,'raw_files_modified':False}
(ROOT/'evaluation/task06/portable-links.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# Навигация по историческим свидетельствам','','Raw reports, frozen runs и logs сохранены побайтно. Их старые относительные/абсолютные пути относятся к месту первоначального исполнения. Ниже — отдельные читаемые копии с проверенными относительными ссылками; они не заменяют первичный evidence. Полная карта преобразований — `evaluation/task06/portable-links.json`.','','| Исторический источник | Переносимая навигационная копия |','|---|---|']
for record in records:
    lines.append(f"| `{record['source']}` | [Открыть]({Path(record['view']).relative_to('submission').as_posix()}) |")
(ROOT/'submission/EVIDENCE_MAP.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({'copies':len(records),'unresolved':unresolved},ensure_ascii=False))
