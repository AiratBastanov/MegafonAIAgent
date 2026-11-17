"""Local Markdown/text -> PDF and raster views of actual files. No model or web calls."""
import argparse
from datetime import datetime,timezone
import hashlib
import html
import importlib.metadata
import io
import json
from pathlib import Path
import re
import fitz
import markdown

CSS='''
body { font-family: sans-serif; font-size: 10.5pt; line-height: 1.35; color:#162334; }
h1 { font-size:23pt; color:#144a65; margin-top:8pt; }
h2 { font-size:16pt; color:#144a65; margin-top:18pt; }
h3 { font-size:12pt; color:#144a65; }
p { margin-bottom:7pt; }
table { border-collapse:collapse; width:100%; font-size:9pt; margin:8pt 0; }
th { background-color:#e7f0f5; text-align:left; }
td,th { border:0.5pt solid #a2b5c4; padding:5pt; vertical-align:top; }
pre { font-size:8pt; white-space:pre-wrap; background-color:#f1f4f7; padding:7pt; }
code { font-size:9pt; }
img { width:450pt; max-width:100%; }
blockquote { border-left:3pt solid #66a4bb; padding-left:9pt; color:#344c5c; }
a { color:#086089; }
'''

def pdf(source,output,title=None):
    text=source.read_text(encoding='utf-8')
    body=markdown.markdown(text,extensions=['tables','fenced_code']) if source.suffix=='.md' else '<pre>'+html.escape(text)+'</pre>'
    if title:body='<h1>'+html.escape(title)+'</h1>'+body
    story=fitz.Story(html=body,user_css=CSS,archive=fitz.Archive(str(source.parent)))
    output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists():raise FileExistsError(output)
    page=fitz.paper_rect('a4');area=page+(38,38,-38,-42)
    def rectfn(index,filled):
        if index>=100:raise ValueError('Unexpected pagination; inspect document')
        return page,area,None
    document=story.write_with_links(rectfn)
    pages=len(document)
    for i,p in enumerate(document):
        p.insert_text((38,820),f'TASK06 | {i+1} / {pages}',fontsize=8,color=(.3,.4,.5))
    document.save(output);document.close()
    return pages

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--title');p.add_argument('--png-dir',type=Path);p.add_argument('--pages',default='all')
    a=p.parse_args()
    if a.source.suffix.lower()=='.pdf':
        document=fitz.open(a.source)
        count=len(document)
    else:
        count=pdf(a.source,a.output,a.title);document=fitz.open(a.output)
    images=[]
    if a.png_dir:
        a.png_dir.mkdir(parents=True,exist_ok=True)
        page_ids=range(count) if a.pages=='all' else [int(x)-1 for x in a.pages.split(',')]
        for i in page_ids:
            target=a.png_dir/f'{a.output.stem}-p{i+1:02}.png'
            if target.exists():raise FileExistsError(target)
            document[i].get_pixmap(matrix=fitz.Matrix(1.6,1.6),alpha=False).save(target)
            images.append({'file':target.as_posix(),'page':i+1,'sha256':digest(target)})
    print(json.dumps({'observed_at':datetime.now(timezone.utc).isoformat(),'source':a.source.as_posix(),
        'source_sha256':digest(a.source),'pages':count,'images':images,
        'renderer':{n:importlib.metadata.version(n) for n in ('Markdown','PyMuPDF')},
        'scope':'Rendered view of actual file; not a Codex UI screenshot or proof of independent host execution'},ensure_ascii=False))
