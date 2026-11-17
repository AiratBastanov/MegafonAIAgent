"""Preserve historical files and derive a disposable authentic checkpoint copy."""
from pathlib import Path
import json, shutil, zipfile
from observe import ROOT, BASE, sha, write_new, now, manifest

protected=['projects/demo-001','projects/demo-002','projects/task06-rehearsal',
           'evaluation/task03','evaluation/task04','evaluation/task05','evaluation/task06',
           'dist/MegafonAIAgent-TASK06-rc1.zip','dist/validation-rc1',
           'docs/TASK06_REPORT.md','docs/TASK06_REVIEW_PACKET.md']
before={}
for name in protected:
    p=ROOT/name
    for f in ([p] if p.is_file() else p.rglob('*')):
        if f.is_file() and '__pycache__' not in f.parts: before[f.relative_to(ROOT).as_posix()]=sha(f)
write_new(BASE/'preservation-before.json',{'at':now(),'files':before})
for name in ('DEVELOPMENT_STATE','SUBMISSION_READINESS'):
    dest=ROOT/f'docs/history/{name}-before-TASK07.md'
    if dest.exists(): raise FileExistsError(dest)
    shutil.copyfile(ROOT/f'docs/{name}.md',dest)
for name in ('README.md','PROJECT_DESCRIPTION.md','PROJECT_DESCRIPTION.pdf','DEMO_RUNBOOK.md','EVIDENCE_MAP.md'):
    p=ROOT/'submission'/name
    dest=BASE/'prior-jury'/name;dest.parent.mkdir(exist_ok=True)
    if dest.exists():raise FileExistsError(dest)
    shutil.copyfile(p,dest)
source=ROOT/'evaluation/task06/continuation-checkpoint.zip'
origin=json.loads((ROOT/'evaluation/task06/continuation-manifest.json').read_text(encoding='utf-8'))
assert sha(source)==origin['archive_sha256']
workspace=BASE/'demo-workspace'
assert not workspace.exists()
with zipfile.ZipFile(source) as z:
    assert z.testzip() is None
    assert all((workspace/n).resolve().is_relative_to(workspace.resolve()) for n in z.namelist())
    z.extractall(workspace)
originals={x['path']:x['sha256'] for x in origin['files']}
assert manifest(workspace)==originals
runtime=[x for x in originals if x=='AGENTS.md' or x.startswith(('scripts/','knowledge/'))]
differences=[x for x in runtime if sha(ROOT/x)!=originals[x]]
assert not differences, differences
write_new(BASE/'continuation-before.json',{'at':now(),'origin_archive':str(source.relative_to(ROOT)),
    'origin_archive_sha256':sha(source),'origin_captured_at':origin['captured_at'],
    'runtime_matches_current':True,'files':originals,'workspace':workspace.relative_to(ROOT).as_posix(),
    'starting_revision':1,'later_answers_supplied':False})
write_new(BASE/'start.json',{'recorded_at':now(),'initial_reading_before_record':True,
    'coordinator_model_exact':None,'tokens':None,'charges':None,'human_active_seconds':None})
print('Historical files preserved; authentic checkpoint derived; 46 hashes and current runtime verified.')
