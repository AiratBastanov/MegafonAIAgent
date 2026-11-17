"""Отдельный новый процесс Codex на подлинном незавершённом проекте."""
from pathlib import Path
import json
import shutil
import sys
sys.stdout.reconfigure(encoding="utf-8")
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from evaluation.task07 import observe
observe.BASE = BASE


def main():
    origin = ROOT/'evaluation/task06/continuation-checkpoint.zip'
    workspace = BASE/'continuation-workspace'
    assert not workspace.exists()
    workspace.mkdir()
    with zipfile.ZipFile(origin) as archive:
        assert archive.testzip() is None
        assert all((workspace/n).resolve().is_relative_to(workspace) for n in archive.namelist())
        archive.extractall(workspace)
    # Подлинные project/state/evidence сохранены; только runtime и инструкции новые.
    for name in ('scripts', 'knowledge'):
        shutil.copytree(ROOT/name, workspace/name, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for name in ('AGENTS.md', 'README.md', 'requirements.txt'):
        shutil.copyfile(ROOT/name, workspace/name)
    runtime = {p.relative_to(ROOT).as_posix(): observe.sha(p)
        for name in ('scripts', 'knowledge') for p in (ROOT/name).rglob('*')
        if p.is_file() and '__pycache__' not in p.parts}
    runtime.update({n: observe.sha(ROOT/n) for n in ('AGENTS.md', 'requirements.txt')})
    state = json.loads((workspace/'projects/task06-rehearsal/state/current.json').read_text(encoding='utf-8'))
    observe.write_new(BASE/'continuation-before.json', dict(at=observe.now(), workspace=workspace.relative_to(ROOT).as_posix(),
        source_archive=origin.relative_to(ROOT).as_posix(), source_archive_sha256=observe.sha(origin),
        initial_revision=state['revision'], initial_state_sha256=state['state_sha256'],
        files=observe.manifest(workspace), runtime=runtime, supplied_previous_transcript=False,
        prompt='Продолжи проект task06-rehearsal по сохранённым файлам. Выполни один следующий полезный аналитический шаг, создай его результат и сохрани новую ревизию. После этого остановись.'))
    prompt = json.loads((BASE/'continuation-before.json').read_text(encoding='utf-8'))['prompt']
    codex = shutil.which('codex')
    assert codex
    observe.run('continuation-current', [codex, 'exec', '--json', '--sandbox', 'workspace-write',
        '--skip-git-repo-check', '--color', 'never', prompt], cwd=workspace, timeout=900)


if __name__ == '__main__':
    main()
