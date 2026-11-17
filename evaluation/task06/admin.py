"""TASK06: observations and preservation checks, no model calls or strategy generation."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')

def protected_files():
    roots = ['projects/demo-001', 'projects/demo-002', 'evaluation/task03',
             'evaluation/task05', 'docs/TASK05_REPORT.md', 'docs/TASK05_REVIEW_PACKET.md']
    result = {}
    for name in roots:
        p = ROOT/name
        for f in ([p] if p.is_file() else p.rglob('*')):
            if f.is_file() and '__pycache__' not in f.parts:
                result[f.relative_to(ROOT).as_posix()] = digest(f)
    return result

if __name__ == '__main__':
    command = sys.argv[1]
    if command == 'init':
        write_new(HERE/'preservation-before.json', {'observed_at':datetime.now(timezone.utc).isoformat(), 'files':protected_files()})
        for name in ('DEVELOPMENT_STATE', 'SUBMISSION_READINESS'):
            destination=ROOT/f'docs/history/{name}-before-TASK06.md'
            if destination.exists():
                raise FileExistsError(destination)
            shutil.copyfile(ROOT/f'docs/{name}.md', destination)
        write_new(HERE/'start.json', {'first_observed_clock_utc':'2026-11-16T15:15:38+00:00',
            'recorded_at':datetime.now(timezone.utc).isoformat(),
            'note':'Начальное чтение до первого clock отдельно не измерено. Время клиента Europe/Moscow = UTC+03:00.',
            'model_id':None,'model_settings':None,'tokens':None,'charges':None,'human_active_time':None})
        print('Historical hashes and prior status documents preserved.')
    elif command == 'preserve-check':
        before=json.loads((HERE/'preservation-before.json').read_text(encoding='utf-8'))['files']
        after=protected_files()
        differences=[p for p,h in before.items() if after.get(p)!=h]
        result={'observed_at':datetime.now(timezone.utc).isoformat(),'protected_files':len(before),
                'differences':differences,'passed':not differences}
        write_new(Path(sys.argv[2]),result)
        print(json.dumps(result));sys.exit(bool(differences))
