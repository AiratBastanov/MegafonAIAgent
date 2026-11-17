"""Read-only independent inspection of the previous delivered archive."""
import hashlib
import json
import argparse
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit
from zipfile import ZipFile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
DELIVERY = ROOT / 'dist/Материалы-2026-11-16'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def readj(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

record = {'checked_at_utc': datetime.now(timezone.utc).isoformat(),
          'scope': 'Independent read-only inspection; no old regression rerun'}
archive = DELIVERY / 'Проект.zip'
record['archive'] = {'sha256': sha(archive.read_bytes()), 'bytes': archive.stat().st_size}
with ZipFile(archive) as z:
    names = z.namelist()
    record['archive']['crc_failure'] = z.testzip()
    manifest = json.loads(z.read('MANIFEST.json'))
    external = readj(DELIVERY / 'Проект.manifest.json')
    record['archive']['manifest_equal'] = manifest == external
    record['archive']['file_count'] = len(manifest['files'])
    record['archive']['mismatch'] = []
    for f in manifest['files']:
        data = z.read(f['path'])
        if sha(data) != f['sha256'] or len(data) != f['bytes']:
            record['archive']['mismatch'].append(f['path'])
    record['archive']['unmanifested_generated_metadata'] = sorted(set(names)-{f['path'] for f in manifest['files']})
    record['archive']['unexpected_members'] = sorted(set(names)-{f['path'] for f in manifest['files']}-{'MANIFEST.json', 'CONTENTS.md'})
    record['archive']['unsafe_paths'] = [n for n in names if n.startswith(('/', '\\')) or '..' in Path(n).parts]
    record['archive']['credential_like_names'] = [n for n in names if any(p.lower() in {'.env', 'auth.json', 'credentials', '.aws', '.ssh', '.codex', '.venv'} for p in Path(n).parts)]
    runtime = [n for n in names if n.startswith(('scripts/', 'knowledge/')) or n in {'AGENTS.md', 'requirements.txt'}]
    record['runtime_hashes'] = {n: sha(z.read(n)) for n in runtime}
    record['runtime_workspace_difference'] = [n for n in runtime if not (ROOT/n).is_file() or sha((ROOT/n).read_bytes()) != sha(z.read(n))]
    record['runtime_delivered_extraction_difference'] = [n for n in runtime if not (DELIVERY/'Проект'/n).is_file() or sha((DELIVERY/'Проект'/n).read_bytes()) != sha(z.read(n))]
    prefix='evaluation/task07/demo-workspace/'
    record['continuation_runtime_difference'] = [n for n in runtime if n != 'AGENTS.md' and prefix+n in names and sha(z.read(prefix+n)) != sha(z.read(n))]
    record['continuation_agents'] = z.read(prefix+'AGENTS.md').decode('utf-8')
    record['chronology'] = {}
    pfx=prefix+'projects/task06-rehearsal/state/'
    record['chronology']['actions'] = [json.loads(line) for line in z.read(pfx+'actions.jsonl').decode('utf-8').splitlines() if line.strip()]
    record['chronology']['history'] = []
    for n in sorted(n for n in names if n.startswith(pfx+'history/') and n.endswith('.json')):
        state=json.loads(z.read(n))
        record['chronology']['history'].append({'path': n, 'metadata': {k:v for k,v in state.items() if k not in {'project', 'task', 'sources', 'artifacts', 'claims', 'calculations', 'decisions', 'decision', 'commitments', 'observations', 'reviews', 'open_questions', 'next_actions', 'assumptions', 'resource_usage', 'followup', 'action_log', 'decisions_history'} and not isinstance(v,(dict,list))}})
    record['archive']['media_hashes'] = {n:sha(z.read(n)) for n in ['submission/Описание проекта.pdf','submission/video/Демонстрация.mp4']}
    record['continuation'] = {k:v for k,v in json.loads(z.read('evaluation/task07/continuation-result.json')).items() if k not in {'before_files','after_files'}}
    record['usage'] = {}
    for n in ['evaluation/task07/observations/continuation-cli/stdout.txt', 'evaluation/task07/observations/synthesis-cli/stdout.txt']:
        events=[]
        for lineno, line in enumerate(z.read(n).decode('utf-8').splitlines(),1):
            try: e=json.loads(line)
            except ValueError: continue
            if e.get('type') in {'thread.started','turn.completed','turn.failed'}:
                events.append({'line':lineno,'event':e})
        record['usage'][n]=events

record['standalone_media_hashes']={n:sha((DELIVERY/n).read_bytes()) for n in ['Описание проекта.pdf','Демонстрация.mp4']}
record['current_navigation']={}
for name in ['Начать.html','Проверка.md','Проект/submission/TECHNICAL_APPENDIX.md']:
    file=DELIVERY/name
    txt=file.read_text(encoding='utf-8-sig')
    targets=re.findall(r'(?:href|src)="([^"]+)"',txt) if file.suffix=='.html' else re.findall(r'\]\(([^)]+)\)',txt)
    broken=[]
    local=[]
    for target in targets:
        url=urlsplit(target)
        if url.scheme or url.netloc or not url.path: continue
        local.append(target)
        if not (file.parent/unquote(url.path)).exists(): broken.append(target)
    record['current_navigation'][name]={'local_targets':len(local),'broken':broken}

try:
    from pypdf import PdfReader
    record['pdf_actual']={}
    for name in ['Описание проекта.pdf','Проект/submission/Описание проекта.pdf']:
        file=DELIVERY/name
        pdf=PdfReader(file)
        links=[]
        for pn,page in enumerate(pdf.pages,1):
            for ref in page.get('/Annots',[]):
                ann=ref.get_object(); action=ann.get('/A',{})
                uri=action.get('/URI')
                spec=action.get('/F')
                if uri is None and spec:
                    uri=spec.get('/UF',spec.get('/F')) if hasattr(spec,'get') else spec
                if isinstance(uri,bytes): uri=uri.decode('utf-8')
                if uri:
                    parts=urlsplit(str(uri))
                    if not parts.scheme and not parts.netloc:
                        links.append({'page':pn,'target':str(uri),'exists':(file.parent/unquote(parts.path)).exists()})
        record['pdf_actual'][name]={'pages':len(pdf.pages),'local_links':links,'broken': [l for l in links if not l['exists']]}
except ImportError:
    record['pdf_actual']={'error':'pypdf unavailable in this interpreter'}

parser=argparse.ArgumentParser()
parser.add_argument('--output',type=Path,default=OUT/'baseline-inspection.json')
args=parser.parse_args()
with args.output.open('x',encoding='utf-8') as f:
    f.write(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k not in {'continuation_agents','chronology','runtime_hashes','pdf_actual','continuation'}},ensure_ascii=False,indent=2))
print('Full evidence: evaluation/architecture-review/release-evidence/baseline-inspection.json')
