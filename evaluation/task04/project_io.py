"""Механическая запись наблюдений/кандидатов координатора; не генерирует стратегии."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import project_state as ps
import decision_followup as df
from observe import log, write_new

PROJECT = ROOT / 'evaluation/task04/projects/task04-followup'


def attach(data, path, aid, project=PROJECT):
    data['artifacts'].append(ps.reference(project, path, aid))


def register_source(data, sid, version, project=PROJECT):
    folder = f'evidence/sources/{sid}/v{version}'
    metadata = json.loads((project / folder / 'source.json').read_text(encoding='utf-8'))
    ids = []
    for label, path in [('meta', folder + '/source.json'), ('original', metadata['original']['path']), ('extract', metadata['extract']['path'])]:
        aid = f'{sid}v{version}-{label}'
        attach(data, path, aid, project)
        ids.append(aid)
    data['sources'].append({'id': sid, 'version': version, 'synthetic': metadata['synthetic'], 'artifact_ids': ids})


def publish(data, name, project=PROJECT):
    draft = f'drafts/{name}.json'
    write_new(project / draft, data)
    saved = ps.save_state(project, data)
    log('state_published', project_id=saved['project_id'], revision=saved['revision'], draft=draft,
        state_sha256=saved['state_sha256'], decision_status=saved['decision']['status'])
    return saved


def event_file(path):
    return json.loads((PROJECT / path).read_text(encoding='utf-8'))
