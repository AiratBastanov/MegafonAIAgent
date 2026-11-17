"""Read actual registered documents; no strategic content generated here."""
import argparse,re
from show_economics import ROOT,load_state,scoped_path,only

p=argparse.ArgumentParser();p.add_argument('kind',choices=['options','product-strategy','communication-strategy','validation-plan']);a=p.parse_args()
project=ROOT/'evaluation/task07/demo-workspace/projects/task06-rehearsal'
s=load_state(project);aid=s['decision']['current_outputs'][a.kind]
ref=only(s['artifacts'],lambda x:x['id']==aid)
t=scoped_path(project,ref['path']).read_text(encoding='utf-8')
print('Просмотр документа из проверенной сохранённой версии.\n')
if a.kind=='options':
    rows=[line for line in t.splitlines() if line.startswith('| **')]
    for row in rows:
        cells=row.strip('|').split('|'); print(cells[0].strip().replace('**',''))
        print(cells[-1].strip().replace('**','')+'\n')
else:
    paragraphs=[x for x in t.split('\n\n') if x.strip()]
    if a.kind=='product-strategy':chosen=paragraphs[:4]
    elif a.kind=='communication-strategy':
        start=t.index('## Сообщение');chosen=t[start:].split('\n\n')[:4]
    else:chosen=paragraphs[:4]
    text='\n\n'.join(chosen)
    text=re.sub(r'\[\^\d+\]','',text).replace('**','').replace('## ','').replace('# ','')
    print(text)
