"""Versioned allowlisted archive and fresh extraction checks; never uploads."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,re,sys,zipfile
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from evaluation.task06.package_release import files,EXCLUDED_PARTS
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:json.dump(obj,f,ensure_ascii=False,indent=2)
def build(target):
    entries=sorted(files(ROOT))
    manifest={'created_at':datetime.now(timezone.utc).isoformat(),'release':'TASK07-rc2',
      'scope':'Local demonstrated agent, real video and readable Russian materials; publication separate.',
      'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in entries]}
    target.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED) as z:
        for p in entries:z.write(p,p.relative_to(ROOT).as_posix())
        z.writestr('MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
        z.writestr('CONTENTS.md','# Стратег Фабрики продуктов\n\nНачните с [материалов жюри](submission/README.md).\n\nУстановка — [инструкция запуска](README.md). Полный состав и хеши: MANIFEST.json. Сам реестр и этот индекс не хешируют себя.\n')
    write(target.with_suffix('.manifest.json'),manifest)
    write(target.with_suffix('.identity.json'),{'archive':target.name,'bytes':target.stat().st_size,'sha256':sha(target)})
    print(json.dumps({'archive':str(target),'files':len(entries),'bytes':target.stat().st_size,'sha256':sha(target)},ensure_ascii=False))
def check(archive,destination,output):
    destination=destination.resolve()
    assert destination.is_relative_to(ROOT) and destination!=ROOT and not destination.exists()
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert all((destination/n).resolve().is_relative_to(destination) for n in z.namelist())
        z.extractall(destination)
    manifest=json.loads((destination/'MANIFEST.json').read_text(encoding='utf-8'))
    mismatch=[x['path'] for x in manifest['files'] if sha(destination/x['path'])!=x['sha256']]
    covered=set()
    for name in ('evaluation/task06/portable-links.json','evaluation/task07/portable-links.json','evaluation/provenance-release/portable-links.json'):
        p=destination/name
        if p.exists():
            for row in json.loads(p.read_text(encoding='utf-8'))['copies']:
                for m in row['mappings']:
                    if (destination/m['packaged']).is_file():covered.add((row['source'],m['original']))
    broken=[];historical=[]
    for p in destination.rglob('*.md'):
        text=re.sub(r'```.*?```','',p.read_text(encoding='utf-8-sig'),flags=re.S)
        for raw in re.findall(r'\]\(([^\n)]+)\)',text):
            target=unquote(raw.strip('<>').split('#')[0])
            if not target or re.match(r'^[a-zA-Z]+:',target):continue
            if not (p.parent/target).exists():
                item={'source':p.relative_to(destination).as_posix(),'target':target}
                (historical if (item['source'],target) in covered else broken).append(item)
    forbidden=[];suspect=[]
    patterns=[re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),re.compile(rb'\bgh[pousr]_[A-Za-z0-9]{30,}\b'),re.compile(rb'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{32,}\b')]
    for x in manifest['files']:
        p=destination/x['path']
        if any(v in p.relative_to(destination).parts for v in EXCLUDED_PARTS) or p.name=='.env' or p.name.startswith('.env.'):forbidden.append(x['path'])
        if p.suffix.lower() in ('.md','.txt','.json','.jsonl','.toml','.log') and any(r.search(p.read_bytes()) for r in patterns):suspect.append(x['path'])
    result={'at':datetime.now(timezone.utc).isoformat(),'archive_sha256':sha(archive),'files':len(manifest['files']),
      'crc_pass':True,'hash_mismatch':mismatch,'broken_active_links':broken,'historical_links_with_mapping':historical,
      'forbidden_paths':forbidden,'suspect_secret_paths':suspect,'secret_check_scope':'Allowlisted package only; known token/private-key markers, not a universal detector.',
      'passed':not(mismatch or broken or forbidden or suspect),'extracted':str(destination.relative_to(ROOT))}
    write(output,result);print(json.dumps(result,ensure_ascii=False,indent=2));return result['passed']
if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='mode',required=True)
    b=s.add_parser('build');b.add_argument('--output',type=Path,required=True)
    c=s.add_parser('check');c.add_argument('--archive',type=Path,required=True);c.add_argument('--extract',type=Path,required=True);c.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.mode=='build':build(a.output)
    else:sys.exit(0 if check(a.archive,a.extract,a.output) else 1)
