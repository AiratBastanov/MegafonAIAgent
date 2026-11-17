"""Локальная приёмка по сохранённым файлам и отдельным CLI процессам, не fresh host."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

from project_io import ROOT, PROJECT, ps, df
from observe import manifest, write_new, log

def command(script, *args):
    cp = subprocess.run([sys.executable, str(ROOT / script), *args], capture_output=True, encoding='utf-8',
                        env={**os.environ, 'PYTHONIOENCODING': 'cp1251'}, timeout=30)
    assert cp.returncode == 0, cp.stderr
    return json.loads(cp.stdout), cp

loaded, process = command('scripts/project_state.py', 'load', '--project', str(PROJECT))
data = loaded['state']
assert loaded['ok'] and data['revision'] == 11 and not loaded['warnings']
write_new(ROOT / 'evaluation/task04/separate-final-load.json', loaded)
view, _ = command('scripts/decision_followup.py', 'view', '--project', str(PROJECT),
                  '--as-of', '2026-12-19T12:00:00+03:00', '--timezone', '+03:00', '--clock', 'simulated')
write_new(ROOT / 'evaluation/task04/separate-final-followup.json', view)
assert view['decision_status'] == 'simulated_accepted' and len(view['history']) == 1
assert len(view['commitments']) == 4
commitments = {c['id']: c for c in view['commitments']}
assert commitments['K-PROTOCOL']['status'] == 'completed' and commitments['K-PROTOCOL']['completion_evidence']
assert commitments['K-CAPABILITY']['status'] != 'completed' and 'overdue' in commitments['K-CAPABILITY']['attention']
assert {'blocked', 'unassigned'} <= set(commitments['K-BUDGET']['attention'])
assert 'overdue' not in commitments['K-BUDGET']['attention']
assert view['metrics'][0]['window_state'] == 'ended_evidence_required'
assert any(r['event_id'] == 'WITHDRAW-01' and r['status'] == 'revised' and r['owner_review_required'] for r in view['reviews'])
assert any(r['event_id'] == 'ECON-RECHECK-01' and r['status'] == 'reviewed_unchanged' for r in view['reviews'])
assert any(r['event_id'] == 'NONMATERIAL-01' and not r['impact']['affected'] for r in view['reviews'])
assert view['next_action'] == data['next_action']
baseline = json.loads((ROOT / 'evaluation/task04/baseline.json').read_text(encoding='utf-8'))
preserved = {}
for folder, records in baseline.items():
    current = manifest(folder)
    changed = [p for p, h in records.items() if current.get(p) != h]
    if folder == 'projects/demo-002':
        allowed = {'projects/demo-002/README.md': 'projects/demo-002/evidence/readme-before-task04.md',
                   'projects/demo-002/state/current.json': 'projects/demo-002/state/history/r000004.json',
                   'projects/demo-002/state/previous.json': 'projects/demo-002/state/history/r000003.json'}
        assert set(changed) <= set(allowed), changed
        for old in changed:
            import hashlib
            assert hashlib.sha256((ROOT / allowed[old]).read_bytes()).hexdigest() == records[old]
    else:
        assert not changed and current == records, folder
    preserved[folder] = {'baseline_files': len(records), 'changed_paths': changed,
                         'prior_bytes_preserved': True, 'current_files': len(current)}
histories = {}
for project in [PROJECT, ROOT / 'projects/demo-001', ROOT / 'projects/demo-002']:
    revisions = []
    for path in sorted((project / 'state/history').glob('r*.json')):
        state = ps._read_json(path, ps.DEFAULT_MAX_BYTES)
        ps.validate_state(project, state, require_saved=True)
        revisions.append(state['revision'])
    histories[project.name] = revisions
    if project != PROJECT:
        canonical, _ = command('scripts/project_state.py', 'load', '--project', str(project))
        assert canonical['state']['decision']['status'] == 'awaiting_decision'
        assert canonical['state']['revision'] == 5
numeric = json.loads((PROJECT / 'evidence/economic-impact-v1.json').read_text(encoding='utf-8'))
assert 'claim:C007' not in {x['node'] for x in numeric['affected']}
assert any(x['node'] == 'condition:G-ECONOMICS' for x in numeric['affected'])
check = json.loads((PROJECT / 'evidence/nonmaterial-check-v1.json').read_text(encoding='utf-8'))
assert check['decision_count'] == 1 and check['commitment_count'] == 4 and check['foreign_project_rejected']
result = {'status': 'TASK04_FOLLOWUP_LOCAL_PASS', 'observed_at': datetime.now(timezone.utc).isoformat(),
          'project_id': PROJECT.name, 'revision': data['revision'], 'state_sha256': data['state_sha256'],
          'independent_python_load': True, 'interpreter': sys.executable, 'python': sys.version, 'platform': sys.platform,
          'synthetic_evaluation': True, 'preservation': preserved, 'validated_histories': histories,
          'active_owner_review': True, 'decision_count': 1, 'commitments': 4, 'real_business_approval': False,
          'FRESH_HOST_SAVE_RELOAD': 'NOT_VERIFIED', 'official_brief_conformity': 'NOT_VERIFIED'}
write_new(ROOT / 'evaluation/task04/acceptance.json', result)
log('demo_local_acceptance', **result)
print(json.dumps(result, ensure_ascii=False, indent=2))
