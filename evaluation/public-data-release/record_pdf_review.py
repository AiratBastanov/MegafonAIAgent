"""Preserve the old PDF aliases, install the inspected version and record all rendered pages."""
from pathlib import Path
import hashlib
import json
import shutil
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
source=ROOT/'submission/Описание проекта-публикация-v2.pdf'
for name in ('Описание проекта.pdf','PROJECT_DESCRIPTION.pdf'):
    target=ROOT/'submission'/name
    backup=HERE/'before/submission'/name
    assert backup.exists() and sha(target)==sha(backup)
    shutil.copyfile(source,target)
frames=[]
for p in sorted((ROOT/'_public-data-release/pdf-v2').glob('*.png')):
    target=HERE/'pdf-review'/p.name
    target.parent.mkdir(parents=True,exist_ok=True)
    assert not target.exists()
    shutil.copyfile(p,target)
    frames.append({'path':target.relative_to(ROOT).as_posix(),'sha256':sha(target)})
assert len(frames)==5
report={'pages':5,'reviewed_pages':[1,2,3,4,5],'pdf_sha256':sha(source),
        'review':'Every rendered page visually inspected by coordinator. Cyrillic, tables, screenshots, complete rows, page breaks and footers readable; no clipping or blank spillover. First six-page attempt preserved; prose shortened without reducing font.',
        'images':frames,'passed':True}
with (HERE/'pdf-review.json').open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
print('Inspected five-page PDF installed; old bytes preserved.')
