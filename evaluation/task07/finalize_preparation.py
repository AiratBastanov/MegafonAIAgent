"""Verify the exact portable-instruction suffix; preserve first strict-check failure."""
import json
from observe import ROOT,BASE,sha,manifest,write_new,now
origin=json.loads((ROOT/'evaluation/task06/continuation-manifest.json').read_text(encoding='utf-8'))
workspace=BASE/'demo-workspace'
expected={x['path']:x['sha256'] for x in origin['files']}
assert manifest(workspace)==expected
suffix='\n\nСреда изолированной копии: сначала прочитай `RUNTIME.md`; работай только с локальным проектом этой копии.\n'
current=(ROOT/'AGENTS.md').read_text(encoding='utf-8').rstrip()
portable=(workspace/'AGENTS.md').read_text(encoding='utf-8')
assert portable==current+suffix
runtime=[x for x in expected if x.startswith(('scripts/','knowledge/'))]
assert all(sha(ROOT/x)==expected[x] for x in runtime)
write_new(BASE/'preparation-first-failure.json',{'recorded_at':now(),'command':'python -X utf8 evaluation/task07/prepare.py',
    'exception':"AssertionError: ['AGENTS.md']",'classification':'overly strict validation, not runtime drift',
    'observable_outcome':'46 checkpoint files extracted and preserved; current scripts/knowledge match; portable AGENTS has intentional RUNTIME.md isolation suffix',
    'correction':'Validate exact suffix and all remaining runtime hashes; no checkpoint bytes modified; do not rerun destructive initialization.'})
write_new(BASE/'continuation-before.json',{'at':now(),'origin_archive':'evaluation/task06/continuation-checkpoint.zip',
    'origin_archive_sha256':origin['archive_sha256'],'origin_captured_at':origin['captured_at'],
    'runtime_matches_current':True,'portable_agents_suffix_verified':True,'files':expected,
    'workspace':workspace.relative_to(ROOT).as_posix(),'starting_revision':1,'later_answers_supplied':False})
write_new(BASE/'start.json',{'recorded_at':now(),'initial_reading_before_record':True,
    'coordinator_model_exact':None,'tokens':None,'charges':None,'human_active_seconds':None})
print('46/46 files verified; current tools match; portable isolation instruction verified.')
