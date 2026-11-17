"""Проверка доставляемых ссылок/снимка и неизменности после финальной упаковки."""
from datetime import datetime, timezone
import ast
import hashlib
import json
import re
from pathlib import Path
from project_io import ROOT, PROJECT, ps
from observe import manifest, write_new

docs = [ROOT / x for x in ['README.md', 'AGENTS.md', 'docs/DEVELOPMENT_STATE.md', 'docs/TASK04_REPORT.md',
                            'docs/TASK04_REVIEW_PACKET.md', 'knowledge/procedures/decision-followup.md',
                            'knowledge/record-contracts.md', 'knowledge/tool-contracts.md']]
broken, checked = [], 0
deferred = ROOT / 'evaluation/task04/resource-accounting.json'
for path in docs:
    content = path.read_text(encoding='utf-8')
    assert '\ufffd' not in content, path
    for target in re.findall(r'\]\(([^)]+)\)', content):
        if target.startswith(('http:', 'https:', '#')):
            continue
        destination = (path.parent / target.split('#')[0]).resolve()
        checked += 1
        if not destination.exists() and destination != deferred:
            broken.append({'document': str(path.relative_to(ROOT)), 'target': target})
assert not broken, broken
data = ps.load_state(PROJECT)
assert data['revision'] == 11
packet = (ROOT / 'docs/TASK04_REVIEW_PACKET.md').read_text(encoding='utf-8')
for name, aid in data['decision']['current_outputs'].items():
    artifact = next(a for a in data['artifacts'] if a['id'] == aid)
    assert (PROJECT / artifact['path']).read_text(encoding='utf-8').rstrip() in packet
baseline = json.loads((ROOT / 'evaluation/task04/baseline.json').read_text(encoding='utf-8'))
for folder in ['projects/demo-001', 'evaluation/task03/continuation-workspace', 'evaluation/task03/fresh-session-01']:
    assert manifest(folder) == baseline[folder]
for name in ['demo-001', 'demo-002']:
    canonical = ps.load_state(ROOT / 'projects' / name)
    assert canonical['revision'] == 5 and canonical['decision']['status'] == 'awaiting_decision'
test_source = (ROOT / 'tests/test_followup.py').read_text(encoding='utf-8')
test_count = sum(isinstance(node, ast.FunctionDef) and node.name.startswith('test_') for node in ast.walk(ast.parse(test_source)))
assert test_count == 17
log = (ROOT / 'evaluation/task04/observations/regression-final-02/stderr.txt').read_text(encoding='utf-8')
assert 'Ran 81 tests' in log and log.rstrip().endswith('OK')
result = {'observed_at': datetime.now(timezone.utc).isoformat(), 'passed': True, 'local_links_checked': checked,
          'broken_links': broken, 'resource_accounting_pending_final_capture': True, 'complete_outputs_in_packet': 5,
          'project_id': data['project_id'], 'revision': 11, 'decision': data['decision']['status'],
          'canonical_decisions': 'awaiting_decision', 'continuation_and_logs_unchanged': True,
          'report_sha256': hashlib.sha256((ROOT / 'docs/TASK04_REPORT.md').read_bytes()).hexdigest(),
          'packet_sha256': hashlib.sha256((ROOT / 'docs/TASK04_REVIEW_PACKET.md').read_bytes()).hexdigest()}
write_new(ROOT / 'evaluation/task04/delivery-check.json', result)
print(json.dumps(result, ensure_ascii=False, indent=2))
