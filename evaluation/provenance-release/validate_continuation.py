"""Отдельный процесс проверяет новый результат; не имитирует запуск LLM."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'scripts'))
import project_state as ps


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    before = json.loads((BASE/'continuation-before.json').read_text(encoding='utf-8'))
    workspace = ROOT/before['workspace']
    project = workspace/'projects/task06-rehearsal'
    observation = BASE/'observations/continuation-current-supported'
    process = json.loads((observation/'result.json').read_text(encoding='utf-8'))
    events = [json.loads(line) for line in (observation/'stdout.txt').read_text(encoding='utf-8').splitlines() if line.strip()]
    threads = [e['thread_id'] for e in events if e['type']=='thread.started']
    turns = [e for e in events if e['type']=='turn.completed']
    assert process['returncode'] == 0 and len(threads)==1 and turns, 'Нет завершённого нового Codex'
    assert all(sha(workspace/n)==h and sha(ROOT/n)==h for n,h in before['runtime'].items()), 'Runtime отличается'
    # load проверяет весь актуальный state, артефакты и историческое происхождение.
    state = ps.load_state(project)
    assert state['revision'] > before['initial_revision']
    old = json.loads((project/'state/history/r000001.json').read_text(encoding='utf-8'))
    assert old['state_sha256']==before['initial_state_sha256']
    draft_path = project/'drafts/checkpoint-v2.json'
    draft = json.loads(draft_path.read_text(encoding='utf-8'))
    assert draft['revision'] == old['revision'] and draft['state_sha256'] == old['state_sha256']
    protected = {n:h for n,h in before['files'].items() if n.startswith('projects/') and n!='projects/task06-rehearsal/state/current.json'}
    assert all(sha(workspace/n)==h for n,h in protected.items()), 'Изменены исходные файлы'
    new_artifacts = [a for a in state['artifacts'] if a['id'] not in {a['id'] for a in old['artifacts']}]
    assert any(a['path'].endswith('analysis-v1.md') for a in new_artifacts), 'Нет нового аналитического артефакта'
    for path in sorted((project/'state/history').glob('r*.json')):
        ps.validate_state(project, ps._read_json(path, ps.DEFAULT_MAX_BYTES), require_saved=True)
    commands = [e['item'] for e in events if e['type']=='item.completed' and e.get('item',{}).get('type')=='command_execution']
    failures = [{'id':i['id'],'command':i['command'],'exit_code':i['exit_code']} for i in commands if i['exit_code']!=0]
    result = dict(at=datetime.now(timezone.utc).isoformat(), checked_by='separate Python process after fresh Codex',
        thread_id=threads[0], historical_thread_id='01a1e533-4f9f-7b03-8e5b-1ba142270987',
        revision=state['revision'], state_sha256=state['state_sha256'], initial_revision=old['revision'],
        initial_state_sha256=old['state_sha256'], preserved_initial_files=len(protected),
        runtime=before['runtime'], new_artifacts=new_artifacts, elapsed_seconds=process['elapsed_seconds'],
        usage=turns[-1].get('usage'), model_reported=None, model_note='Точный вариант модели не сообщён JSONL этого CLI',
        completed_commands=len(commands), failed_commands=failures,
        source_identity_history_valid=True, draft_base_preserved=True,
        draft_path=draft_path.relative_to(project).as_posix(), draft_sha256=sha(draft_path),
        passed=True)
    with (BASE/'continuation-result.json').open('x',encoding='utf-8') as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k not in ('runtime','new_artifacts','failed_commands')},ensure_ascii=False))


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
