"""Повтор после диагноза сетевых прав; те же учётные данные, новый процесс."""
from pathlib import Path
import json
import shutil
import sys
sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from evaluation.task07 import observe
observe.BASE = BASE
before = json.loads((BASE/'continuation-before.json').read_text(encoding='utf-8'))
workspace = ROOT/before['workspace']
actual = observe.manifest(workspace)
assert all(actual.get(n) == h for n,h in before['files'].items())
assert {n:h for n,h in actual.items() if n.startswith('projects/')} == {
    n:h for n,h in before['files'].items() if n.startswith('projects/')}
observe.run('continuation-current-supported', [shutil.which('codex'), 'exec', '--json',
    '--sandbox', 'workspace-write', '--skip-git-repo-check', '--color', 'never', before['prompt']],
    cwd=workspace, timeout=900)
