import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path('scripts').resolve()))
import project_state as ps

states = {}
for branch in ('familiar', 'variant'):
    root = Path('branches') / branch / 'projects/task04-followup'
    data = ps.load_state(root)
    states[branch] = data
    decision = data['decision']
    print(json.dumps({
        'branch': branch, 'revision': data['revision'], 'state_sha256': data['state_sha256'],
        'decision_status': decision['status'],
        'event_ids': [e['id'] for e in decision['events']],
        'reviews': decision['reviews'],
        'commitments': decision['commitments'],
        'metrics': [{'id': m['id'], 'window': m['window']} for m in decision['metrics']],
        'claim_statuses': [{'id': c['id'], 'status': c.get('status')} for c in data['claims']],
    }, ensure_ascii=False, indent=2))

left, right = states['familiar'], states['variant']
print(json.dumps({'same_business_fields': {
    k: left[k] == right[k] for k in ('decision', 'claims', 'sources', 'artifacts', 'next_action')
}}, ensure_ascii=False))
root = Path('branches/familiar/projects/task04-followup')
for name in ('evidence/sources/S005/v1/original.txt',
             'inputs/owner-instruction-v1.md', 'outputs/v2/validation-plan.md',
             'outputs/v2/product-strategy.md', 'outputs/v2/communication-strategy.md',
             'outputs/v2/options.md', 'outputs/v2/situation.md'):
    print('\nFILE ' + str(root / name))
    print((root / name).read_text(encoding='utf-8'))
extract = json.loads((root / 'evidence/sources/S002/v2/extract.json').read_text(encoding='utf-8'))
print(json.dumps({'economics_E3': [c for s in extract['sheets'] for c in s['cells'] if c['locator'] == "'Экономика'!E3"]}, ensure_ascii=False))
print('FIRST_CAPTURE ' + Path('logs/q1-bootstrap-read-utf8/result.json').read_text(encoding='utf-8'))
