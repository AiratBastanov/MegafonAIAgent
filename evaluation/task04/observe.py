"""Наблюдения TASK04: время/команды/хеши, без стратегий и LLM-цикла."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def log(action, **details):
    event = {'observed_at': datetime.now(timezone.utc).isoformat(), 'action': action, **details}
    with (BASE / 'actions.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(event, ensure_ascii=False) + '\n')


def manifest(folder):
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT / folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def run(name, args):
    start = datetime.now(timezone.utc).isoformat()
    counter = time.monotonic()
    result = subprocess.run(args, cwd=ROOT, capture_output=True, encoding='utf-8',
                            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}, timeout=180)
    elapsed = time.monotonic() - counter
    folder = BASE / 'observations' / name
    folder.mkdir(parents=True, exist_ok=False)
    (folder / 'stdout.txt').write_text(result.stdout, encoding='utf-8')
    (folder / 'stderr.txt').write_text(result.stderr, encoding='utf-8')
    meta = {'command': args, 'started_at': start, 'ended_at': datetime.now(timezone.utc).isoformat(),
            'elapsed_seconds': elapsed, 'returncode': result.returncode, 'interpreter': sys.executable}
    write_new(folder / 'result.json', meta)
    log('command', observation=name, **meta)
    print(json.dumps(meta, ensure_ascii=False))
    return result


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if sys.argv[1] == 'baseline':
        folders = ['projects/demo-001', 'projects/demo-002', 'evaluation/task03/continuation-workspace',
                   'evaluation/task03/fresh-session-01']
        write_new(BASE / 'baseline.json', {p: manifest(p) for p in folders})
        log('baseline', folders=folders, interpreter=sys.executable, python=sys.version,
            development_started_at='2026-11-16T11:36:25+00:00', tokens=None, charges=None,
            human_active_time=None, exact_model=None)
        print('Исходные хеши сохранены')
    elif sys.argv[1] == 'run':
        result = run(sys.argv[2], [sys.executable, *sys.argv[3:]])
        print(result.stdout[-2400:])
        print(result.stderr[-2400:])
        raise SystemExit(result.returncode)
