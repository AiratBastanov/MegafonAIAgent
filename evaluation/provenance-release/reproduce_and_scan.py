"""Одноразовое воспроизведение старого дефекта и чтение сохранённых историй."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
import project_state as ps


def write(name, value):
    with (BASE / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def main():
    p = BASE / 'reproduction/nonadjacent'
    p.mkdir(parents=True, exist_ok=True)
    assert not (p / 'state').exists()
    def origin(num):
        path = p / f'A{num}.txt'
        path.write_text(f'Учебное происхождение A{num}; разные байты', encoding='utf-8')
        return ps.reference(p, path.name, f'A{num}')
    data = dict(schema_version=1, project_id=p.name, objective='Проверка сохранения происхождения',
        decision_question='Как сохранить identity?', stage='research', completed=[], unresolved_questions=[],
        pending_actions=[], next_action='Проверить источник', artifacts=[origin(1)],
        sources=[dict(id='S', version=1, artifact_ids=['A1'], synthetic=True)], claims=[],
        decision=dict(format_version=2, status='proposed', question='Что проверить?', proposed_option='Проверить',
            owner='unassigned', history=[], events=[], commitments=[], metrics=[], conditions=[], reviews=[]))
    rows = []
    for num, version, synthetic in [(1, 1, True), (2, 2, True), (3, 1, False)]:
        if num > 1:
            data = ps.load_state(p)
            data['artifacts'].append(origin(num))
            data['sources'] = [dict(id='S', version=version, artifact_ids=[f'A{num}'], synthetic=synthetic)]
        saved = ps.save_state(p, data)
        loaded = ps.load_state(p)
        rows.append(dict(revision=saved['revision'], sources=loaded['sources'], state_sha256=loaded['state_sha256']))
    write('reproduction.json', dict(runtime_sha256=hashlib.sha256((ROOT/'scripts/project_state.py').read_bytes()).hexdigest(),
        accepted_all_three=True, decision_format_version=2, evaluation_present=False, base_full_load=True,
        all_origins_retained=True, states=rows))
    reports = []
    for current in sorted(list((ROOT/'projects').rglob('state/current.json')) + list((ROOT/'evaluation').rglob('state/current.json'))):
        if BASE in current.parents:
            continue
        project = current.parent.parent
        identities, conflicts, invalid, count = {}, [], [], 0
        for path in sorted((project/'state/history').glob('r*.json')):
            try:
                state = ps._read_json(path, ps.DEFAULT_MAX_BYTES)
                if ps._checksum(state) != state['state_sha256']:
                    raise ValueError('checksum')
                arts = {a['id']: a for a in state['artifacts']}
                for src in state['sources']:
                    key = (src['id'], src['version'])
                    value = {'synthetic': src['synthetic'], 'artifacts': sorted([arts[a] for a in src['artifact_ids']], key=lambda x: x['id'])}
                    if key in identities and identities[key]['value'] != value:
                        conflicts.append({'id': key[0], 'version': key[1], 'first': identities[key]['path'], 'other': path.name})
                    else:
                        identities.setdefault(key, dict(value=value, path=path.name))
                count += 1
            except Exception as e:
                invalid.append(dict(file=path.name, error=f'{type(e).__name__}: {e}'))
        reports.append(dict(project=project.relative_to(ROOT).as_posix(), snapshots=count,
            identities=len(identities), conflicts=conflicts, unreadable=invalid))
    write('history-audit-before.json', reports)
    print(json.dumps({'reproduction': rows, 'projects_scanned': len(reports),
        'conflicts': [x for x in reports if x['conflicts']], 'unreadable': [x for x in reports if x['unreadable']]}, ensure_ascii=False))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
