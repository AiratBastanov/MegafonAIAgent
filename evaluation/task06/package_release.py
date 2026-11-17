"""Allowlisted local release ZIP; deterministic file checks, no uploads."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT=Path(__file__).resolve().parents[2]
TOP_FILES=('README.md','AGENTS.md','requirements.txt','.gitignore','DescriptionMegafonAIAgent.txt')
TOP_DIRS=('docs','knowledge','scripts','tests','projects','evaluation','submission','third_party')
EXCLUDED_PARTS={'.venv','.venv-export','__pycache__','.git','.codex','.agents','.aws','node_modules','.pytest_cache'}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def files(root):
    for name in TOP_FILES:
        if (root/name).is_file():yield root/name
    for name in TOP_DIRS:
        for p in (root/name).rglob('*'):
            if not p.is_file():continue
            relative=p.relative_to(root)
            if any(part in EXCLUDED_PARTS for part in relative.parts):continue
            if p.name=='.env' or p.name.startswith('.env.') or p.suffix.lower() in ('.pyc','.pyo','.pem','.key'):
                continue
            if p.is_symlink():raise ValueError('Symlink in package: '+str(relative))
            yield p

def build(version):
    dist=ROOT/'dist';dist.mkdir(exist_ok=True)
    target=dist/f'MegafonAIAgent-TASK06-{version}.zip'
    manifest={'release':version,'created_at':datetime.now(timezone.utc).isoformat(),
              'scope':'Local release candidate; external acceptance and independent LLM/video gaps remain separate.',
              'files':[]}
    all_files=sorted(files(ROOT))
    for p in all_files:
        manifest['files'].append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
    data=json.dumps(manifest,ensure_ascii=False,indent=2)+'\n'
    index='# Состав локального релиза\n\nНачните с [submission/README.md](submission/README.md). Установка — [README.md](README.md).\n\n'
    index+='SHA-256 и размеры всех исходных файлов: `MANIFEST.json`. Сам manifest и этот индекс не включают собственный хеш.\n\n'
    index+='\n'.join(f'- `{x["path"]}` — {x["bytes"]} байт' for x in manifest['files'])+'\n'
    with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED) as z:
        for p in all_files:z.write(p,p.relative_to(ROOT).as_posix())
        z.writestr('MANIFEST.json',data)
        z.writestr('CONTENTS.md',index)
    for suffix,content in (('manifest.json',data),('contents.md',index)):
        with (dist/f'MegafonAIAgent-TASK06-{version}.{suffix}').open('x',encoding='utf-8') as f:f.write(content)
    with (dist/f'MegafonAIAgent-TASK06-{version}.sha256').open('x',encoding='ascii') as f:f.write(sha(target)+'  '+target.name+'\n')
    print(json.dumps({'archive':str(target.relative_to(ROOT)),'sha256':sha(target),'files':len(all_files),'bytes':target.stat().st_size}))

def verify(archive,destination,output,existing=False):
    archive=archive.resolve();destination=destination.resolve();output=output.resolve()
    if not destination.is_relative_to(ROOT) or destination==ROOT:raise ValueError('Extraction must stay inside workspace')
    if destination.exists() != existing:raise ValueError('Use a new extraction directory, or explicitly verify an existing extraction')
    if not output.is_relative_to(ROOT) or output.is_relative_to(destination):raise ValueError('Observation must be outside extraction, inside workspace')
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name in z.namelist():
            assert (destination/name).resolve().is_relative_to(destination)
        if existing:
            actual={p.relative_to(destination).as_posix() for p in destination.rglob('*') if p.is_file()}
            assert actual==set(z.namelist()),'Existing extraction differs from exact ZIP entry set'
        else:
            z.extractall(destination)
    manifest=json.loads((destination/'MANIFEST.json').read_text(encoding='utf-8'))
    errors=[]
    for item in manifest['files']:
        p=destination/item['path']
        if not p.is_file() or sha(p)!=item['sha256']:errors.append(item['path'])
    broken=[]
    for p in destination.rglob('*.md'):
        content=p.read_text(encoding='utf-8-sig')
        content=re.sub(r'```.*?```','',content,flags=re.S)
        for raw in re.findall(r'\]\(([^\n)]+)\)',content):
            link=raw.strip('<>').split('#')[0]
            if not link or re.match(r'^[a-zA-Z]+:',link):continue
            if not (p.parent/link).exists():broken.append({'file':p.relative_to(destination).as_posix(),'target':link})
    navigation=destination/'evaluation/task06/portable-links.json'
    mapping=json.loads(navigation.read_text(encoding='utf-8')) if navigation.exists() else {'copies':[]}
    covered={(r['source'],m['original']) for r in mapping['copies'] for m in r['mappings']
             if (destination/m['packaged']).is_file()}
    active_broken=[x for x in broken if (x['file'],x['target']) not in covered]
    suspect=[]
    secret_patterns=[re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
                     re.compile(rb'\bgh[pousr]_[A-Za-z0-9]{30,}\b'),
                     re.compile(rb'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{32,}\b')]
    forbidden=[]
    for item in manifest['files']:
        p=destination/item['path']
        if any(part in EXCLUDED_PARTS for part in p.relative_to(destination).parts) or p.name=='.env' or p.name.startswith('.env.'):
            forbidden.append(item['path'])
        if p.suffix.lower() in ('.md','.txt','.json','.jsonl','.yaml','.yml','.toml','.log'):
            content=p.read_bytes()
            if any(pattern.search(content) for pattern in secret_patterns):suspect.append(item['path'])
    result={'observed_at':datetime.now(timezone.utc).isoformat(),'archive':str(archive.relative_to(ROOT)),
            'archive_sha256':sha(archive),'extracted':str(destination.relative_to(ROOT)),
            'manifest_files':len(manifest['files']),'hash_errors':errors,'broken_markdown_links':broken,
            'historical_links_resolved_by_map':len(broken)-len(active_broken),'unmapped_broken_links':active_broken,
            'active_navigation_pass':not active_broken,'forbidden_paths':forbidden,'suspect_secret_paths':suspect,
            'secret_check_scope':'Allowlisted package files only; forbidden paths and common token/private-key patterns; synthetic test markers are fixtures, not credentials; not a universal detector.',
            'zip_integrity_pass':True,'content_hashes_pass':not errors}
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k!='broken_markdown_links'}))
    print('Broken relative Markdown links:',len(broken))
    if errors or active_broken or forbidden or suspect:raise SystemExit(1)

if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True)
    b=s.add_parser('build');b.add_argument('--version',required=True)
    v=s.add_parser('verify');v.add_argument('--archive',type=Path,required=True);v.add_argument('--extract',type=Path,required=True);v.add_argument('--output',type=Path,required=True);v.add_argument('--existing-extraction',action='store_true')
    a=p.parse_args()
    if a.command=='build':build(a.version)
    else:verify(a.archive,a.extract,a.output,a.existing_extraction)
