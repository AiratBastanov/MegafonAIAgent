"""Copy initial teaching inputs only; no answers, state or later correction."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[2]
names=('product-brief-v1.pdf','offer-v1.xlsx','DATA_DICTIONARY.md','selection-v1.json',
       'metrics-funnel-v1.json','metrics-economics-v1.json','economics-sensitivity-v1.json','pdf-text-manifest-v1.json')
project=ROOT/'projects/task06-rehearsal'
destination=project/'inputs'
destination.mkdir(parents=True,exist_ok=False)
entries=[]
for name in names:
    source=ROOT/'projects/demo-002/inputs'/name
    shutil.copyfile(source,destination/name)
    entries.append({'original':source.relative_to(ROOT).as_posix(),'copy':'inputs/'+name,
                    'sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
with (destination/'PROVENANCE.json').open('x',encoding='utf-8') as f:
    json.dump({'copied_at':datetime.now(timezone.utc).isoformat(),'synthetic':True,
        'reason':'Новая отдельная репетиция TASK06; исходные байты demo-002, без его state/outputs/коррекции.',
        'files':entries},f,ensure_ascii=False,indent=2)
print(json.dumps({'initial_files':len(entries),'project':'projects/task06-rehearsal'}))
