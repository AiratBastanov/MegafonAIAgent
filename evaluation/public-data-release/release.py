"""Existing allowlisted packaging process; one fresh offline regression, then exact-file sealing."""
from pathlib import Path
from datetime import datetime,timezone
import argparse
import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from evaluation.task06.package_release import files
from evaluation.task07.package import check

WORK=ROOT/'_public-data-release'
DELIVERY=ROOT/'dist/Материалы-2026-11-17-3'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:json.dump(obj,f,ensure_ascii=False,indent=2)
def run(name,command,cwd,checks):
    folder=checks/name
    folder.mkdir(parents=True,exist_ok=False)
    request={'command':list(map(str,command)),'cwd':str(cwd),'started_at':datetime.now(timezone.utc).isoformat(),
             'network':'not needed'}
    write(folder/'request.json',request)
    env=dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
    env.pop('PYTHONPATH',None)
    start=time.monotonic()
    with (folder/'stdout.txt').open('wb') as out,(folder/'stderr.txt').open('wb') as err:
        result=subprocess.run(request['command'],cwd=cwd,env=env,stdout=out,stderr=err,timeout=300)
    report=dict(request,returncode=result.returncode,elapsed_seconds=time.monotonic()-start,
                ended_at=datetime.now(timezone.utc).isoformat(),stdout_sha256=sha(folder/'stdout.txt'),stderr_sha256=sha(folder/'stderr.txt'))
    write(folder/'result.json',report)
    print(name,result.returncode,round(report['elapsed_seconds'],3),flush=True)
    assert result.returncode==0,folder
    return report
def package(archive,destination,proof):
    entries=sorted(files(ROOT))
    checkpoints={'evaluation/checkpoint-before-synthesis-v2.zip','evaluation/checkpoint-before-synthesis.zip',
                 'evaluation/task03/checkpoint-before-conflict.zip','evaluation/task06/continuation-checkpoint.zip'}
    assert all(p.relative_to(ROOT).as_posix() in checkpoints and p.stat().st_size<50*2**20
               for p in entries if p.suffix.lower()=='.zip'), 'Only small historical checkpoint ZIPs are allowed'
    manifest={'created_at':datetime.now(timezone.utc).isoformat(),'release':'public-data-2026-11-17',
              'scope':'Independent UCI evaluation and Russian jury materials; unchanged runtime and canonical history',
              'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in entries]}
    archive.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        for p in entries:z.write(p,p.relative_to(ROOT).as_posix())
        z.writestr('MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
        z.writestr('CONTENTS.md','# Стратег Фабрики продуктов\n\n[Материалы для жюри](submission/README.md) · [Запуск](README.md).\n')
    write(archive.with_suffix('.manifest.json'),manifest)
    write(archive.with_suffix('.identity.json'),{'archive':archive.name,'bytes':archive.stat().st_size,'sha256':sha(archive)})
    with contextlib.redirect_stdout(io.StringIO()):
        passed=check(archive,destination,proof)
    assert passed,proof
    print('Archive, hashes, active links and package scan passed:',len(entries),'files',flush=True)
    return manifest
def candidate():
    assert not (WORK/'candidate').exists()
    package(WORK/'candidate.zip',WORK/'candidate',WORK/'checks/archive.json')
    checks=WORK/'checks'
    run('setup-create',[sys.executable,'-m','venv',WORK/'venv'],WORK/'candidate',checks)
    py=WORK/'venv/Scripts/python.exe'
    run('setup-install',[py,'-m','pip','install','--no-index','--no-cache-dir','--find-links','third_party/wheels','-r','requirements.txt'],WORK/'candidate',checks)
    run('pip-check',[py,'-m','pip','check'],WORK/'candidate',checks)
    run('regression',[py,'-m','unittest','discover','-s','tests','-q'],WORK/'candidate',checks)
    run('release-check',[py,'evaluation/public-data-release/verify_release.py','--output',checks/'release.json'],WORK/'candidate',checks)
def seal():
    assert not DELIVERY.exists()
    baseline=json.loads((WORK/'candidate/MANIFEST.json').read_text(encoding='utf-8'))
    changed=[item['path'] for item in baseline['files'] if sha(ROOT/item['path'])!=item['sha256']]
    allowed={'submission/VERIFICATION.md','docs/SUBMISSION_READINESS.md','docs/DEVELOPMENT_STATE.md',
             'evaluation/public-data-release/WORKLOG.md','evaluation/public-data-release/RESOURCES.md',
             'evaluation/public-data-release/REFERENCES.md','evaluation/public-data-release/references.json',
             'evaluation/public-data-release/release.py'}
    assert set(changed)<=allowed,changed
    package(DELIVERY/'Проект.zip',DELIVERY/'Проект',DELIVERY/'Проверки/archive.json')
    shutil.copytree(WORK/'checks',DELIVERY/'Проверки/candidate')
    shutil.copyfile(ROOT/'submission/video/Демонстрация.mp4',DELIVERY/'Демонстрация.mp4')
    write(DELIVERY/'Проверки/regression-binding.json',{'candidate_zip_sha256':sha(WORK/'candidate.zip'),
          'delivered_zip_sha256':sha(DELIVERY/'Проект.zip'),'changed_after_regression':changed,
          'scope':'Listed editorial reports, reference-record encoding and release allowlist changed after regression. Core runtime, tests, dependencies, datasets, state and PDF remain identical. Final packaging is checked separately.',
          'unchanged_behavior_files':True})
    print('Sealed',DELIVERY,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['candidate','seal'])
    args=parser.parse_args()
    candidate() if args.action=='candidate' else seal()
