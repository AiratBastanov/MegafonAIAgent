"""Проверка точной распаковки текущим offline runtime, без вызовов LLM."""
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import unquote, urlsplit
import argparse
import hashlib
import importlib.metadata
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.project_state import load_state, validate_state, summarize_state
from pypdf import PdfReader


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pdf_links(path):
    reader = PdfReader(path)
    result = {'sha256': sha(path), 'pages': len(reader.pages), 'local_links': []}
    for page_number, page in enumerate(reader.pages, 1):
        for ref in page.get('/Annots', []):
            action = ref.get_object().get('/A', {})
            target = action.get('/URI')
            spec = action.get('/F')
            if spec:
                target = spec.get('/UF', spec.get('/F')) if hasattr(spec, 'get') else spec
            if not isinstance(target, str):
                continue
            parts = urlsplit(target)
            if parts.scheme or parts.netloc or not parts.path:
                continue
            # Filespec is an actual file path. Only URI paths use percent escaping.
            local = target if spec else unquote(parts.path)
            resolved = (path.parent / local).resolve()
            result['local_links'].append({'page': page_number, 'target': target, 'exists': resolved.is_file()})
    result['passed'] = result['pages'] == 5 and len(result['local_links']) == 39 and all(
        item['exists'] for item in result['local_links'])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--standalone', type=Path)
    args = parser.parse_args()
    assert sys.prefix != sys.base_prefix, 'Требуется отдельная среда'
    manifest = json.loads((ROOT/'MANIFEST.json').read_text(encoding='utf-8'))
    for item in manifest['files']:
        path = ROOT/item['path']
        assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256'], item['path']
    report = {'at': datetime.now(timezone.utc).isoformat(), 'python': sys.version,
              'dependencies': {name: importlib.metadata.version(name) for name in ('pypdf', 'openpyxl', 'et-xmlfile')},
              'manifest_files': len(manifest['files']), 'manifest_unchanged': True, 'states': {}}
    expected = json.loads((ROOT/'evaluation/task07/expected-final.json').read_text(encoding='utf-8'))
    for name, wanted in expected['states'].items():
        project = ROOT/name
        state = load_state(project)
        assert (state['revision'], state['state_sha256']) == (wanted['revision'], wanted['state_sha256'])
        history = []
        for path in sorted((project/'state/history').glob('r*.json')):
            saved = json.loads(path.read_text(encoding='utf-8'))
            validate_state(project, saved, require_saved=True)
            history.append(saved['revision'])
        brief = summarize_state(project)
        assert brief['summary']['state_sha256'] == state['state_sha256']
        report['states'][name] = {'revision': state['revision'], 'state_sha256': state['state_sha256'],
                                 'history_valid': history, 'summary_validated': True}
    project = ROOT/'evaluation/task07/demo-workspace/projects/task06-rehearsal'
    state = load_state(project)
    r7 = json.loads((project/'state/history/r000007.json').read_text(encoding='utf-8'))
    assert state['decision']['history'] == r7['decision']['history']
    assert state['decision']['status'] == 'simulated_accepted'
    assert all(item['status'] in ('pending', 'blocked') for item in state['decision']['commitments'])
    assert any(review['owner_review_required'] for review in state['decision']['reviews'])
    proof = json.loads((ROOT/'evaluation/task07/continuation-result.json').read_text(encoding='utf-8'))
    assert sha(project/'state/history/r000002.json') == proof['after_files']['projects/task06-rehearsal/state/current.json']
    for item in proof['new_registered_artifacts']:
        assert sha(project/item['path']) == item['sha256']
    report['continuation_and_followup'] = {'original_choice_preserved': True, 'new_owner_review_required': True,
        'commitments_unperformed': True, 'historical_independent_revision': 2, 'new_llm_run': False}
    current_proof = json.loads((ROOT/'evaluation/provenance-release/continuation-result.json').read_text(encoding='utf-8'))
    current_project = ROOT/'evaluation/provenance-release/continuation-workspace/projects/task06-rehearsal'
    resumed = load_state(current_project)
    assert resumed['state_sha256'] == current_proof['state_sha256']
    assert resumed['revision'] == current_proof['revision']
    for name, digest in current_proof['runtime'].items():
        assert sha(ROOT/name) == digest
        assert sha(ROOT/'evaluation/provenance-release/continuation-workspace'/name) == digest
    for item in current_proof['new_artifacts']:
        assert sha(current_project/item['path']) == item['sha256']
    report['new_independent_continuation'] = {'thread_id': current_proof['thread_id'],
        'revision': resumed['revision'], 'state_sha256': resumed['state_sha256'],
        'artifacts_verified': len(current_proof['new_artifacts']), 'runtime_matches': True}
    report['pdf'] = pdf_links(ROOT/'submission/Описание проекта.pdf')
    assert report['pdf']['passed'], report['pdf']
    if args.standalone:
        report['standalone_pdf'] = pdf_links(args.standalone.resolve())
        assert report['standalone_pdf']['passed'], report['standalone_pdf']
    video = ROOT/'submission/video/Демонстрация.mp4'
    assert sha(video) == '243e78d1c5dfe54073f817b53f9669f608f896fc7ac084e08c72ded332b3e8db'
    report['video_unchanged'] = True
    report['passed'] = True
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({key: value for key, value in report.items() if key not in ('pdf', 'standalone_pdf')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
