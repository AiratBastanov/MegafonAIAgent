"""Read-only package navigation preflight, preserving the first failed check."""
from pathlib import Path
from datetime import datetime,timezone
import json,re,sys
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from evaluation.task06.package_release import files
if __name__=='__main__':
    entries=list(files(ROOT));covered=set();broken=[];historical=[]
    for name in ('evaluation/task06/portable-links.json','evaluation/task07/portable-links.json'):
        for row in json.loads((ROOT/name).read_text(encoding='utf-8'))['copies']:
            for m in row['mappings']:
                if (ROOT/m['packaged']).is_file():covered.add((row['source'],m['original']))
    for p in entries:
        if p.suffix!='.md':continue
        body=re.sub(r'```.*?```','',p.read_text(encoding='utf-8-sig'),flags=re.S)
        for raw in re.findall(r'\]\(([^\n)]+)\)',body):
            target=unquote(raw.strip('<>').split('#')[0])
            if not target or re.match(r'^[a-zA-Z]+:',target):continue
            if not (p.parent/target).exists():
                item={'source':p.relative_to(ROOT).as_posix(),'target':target}
                (historical if (item['source'],target) in covered else broken).append(item)
    result={'at':datetime.now(timezone.utc).isoformat(),'files':len(entries),
       'uncompressed_bytes':sum(p.stat().st_size for p in entries),'broken_active_links':broken,
       'historical_links_with_mapping':len(historical),'passed':not broken}
    with (ROOT/'evaluation/task07/navigation-final-preflight.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(0 if result['passed'] else 1)
