"""Preserve failed candidate files; prepare a typed diagnostic wrapper, not a utility patch."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path('scripts').resolve()))
import project_state as ps
import decision_followup as df


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(value)


for branch in ('familiar', 'variant'):
    root = Path('branches') / branch / 'projects/task04-followup'
    current = ps.load_state(root)
    base = json.loads((root / 'drafts/q2-evidence-base-v1.json').read_text(encoding='utf-8'))
    event = json.loads((root / 'inputs/q2/evidence-change-v1.json').read_text(encoding='utf-8'))
    raw_path = root / 'notes/q2/raw-impact-v1.json'
    raw = json.loads(raw_path.read_text(encoding='utf-8'))
    assert current['state_sha256'] == base['state_sha256'] and current['revision'] == 3
    assert not (root / 'outputs/q2').exists()
    assert not (root / 'drafts/q2-followup-v1.json').exists()
    assert df.reconcile(root, event['id'])['outcome'] == 'absent_from_current'
    expanded = df.impact(root, base, event)
    extra = {a['node'] for a in expanded['affected']} - {a['node'] for a in raw['affected']}
    assert extra == {'artifact:Q2-RAW-IMPACT'}
    assert all(a['id'] != 'Q2-RAW-IMPACT' for a in current['artifacts'])
    base['artifacts'] = [a for a in base['artifacts'] if a['id'] != 'Q2-RAW-IMPACT']
    wrapper = {
        'record_kind': 'diagnostic_impact_report', 'event_id': event['id'],
        'original_file': 'notes/q2/raw-impact-v1.json',
        'original_file_sha256': hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        'report': raw,
        'utility_limitation': 'artifact_json/impact treats any top-level source match as a calculation. A raw impact report is not a calculation or independent source. The report is nested here to preserve its exact content without a top-level source key.',
        'preparation_error': 'q2-prepare assertion failed before any output/state write because registering raw impact added artifact:Q2-RAW-IMPACT as a new root.',
        'recovery': 'Current revision 3 verified; absent_from_current and no output/final draft. Original report and draft retained. Only the new uncommitted diagnostic reference is replaced by this new artifact ID.',
    }
    write_new(root / 'notes/q2/impact-record-v1.json', json.dumps(wrapper, ensure_ascii=False, indent=2) + '\n')
    base['artifacts'].append(ps.reference(root, 'notes/q2/impact-record-v1.json', 'Q2-IMPACT-RECORD'))
    assert df.impact(root, base, event) == raw
    ps.validate_state(root, base)
    write_new(root / 'drafts/q2-evidence-base-v2.json', json.dumps(base, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'branch': branch, 'unexpected_extra_node': sorted(extra),
                      'state_unchanged_revision': 3, 'new_draft': 'drafts/q2-evidence-base-v2.json',
                      'recomputed_impact_matches': True, 'original_files_retained': True}, ensure_ascii=False))

source = Path('q2-prepare.py').read_text(encoding='utf-8')
assert source.count("drafts/q2-evidence-base-v1.json") == 1
source = source.replace('drafts/q2-evidence-base-v1.json', 'drafts/q2-evidence-base-v2.json')
old = '- Q2-NEGATIVE, существенное, закрыто:'
new = ('- Q2-TOOL, ограничение, учтено: первая подготовка остановилась до записи outputs/state, '
       'потому что raw impact с полем source был принят утилитой за ещё один расчёт. '
       'reconcile подтвердил отсутствие события в revision 3; исходный draft/отчёт сохранены. '
       'В state регистрируется новый Q2-IMPACT-RECORD с вложенным точным report, без верхнеуровневого source. '
       'Граф после этого совпадает с исходными 16 узлами. Код утилит не изменён. '
       'Это ограничение типов входных JSON, не новое доказательство или основание пересчёта.\n'
       + old)
assert source.count(old) == 1
source = source.replace(old, new)
source = source.replace("'owner_review_required': True, 'new_choice': False, 'errors': [], 'retries': 0,",
                        "'owner_review_required': True, 'new_choice': False, 'errors': ['Raw impact report was interpreted as a calculation; failed before publication'], 'retries': 1,")
write_new(Path('q2-prepare-v2.py'), source)
print('Created q2-prepare-v2.py; q2-prepare.py and failed stdout/stderr are unchanged.')
