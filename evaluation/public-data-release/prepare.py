"""Preserve edited inputs and inspect the owner-supplied CSV without rewriting it."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import csv
import hashlib
import io
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts.import_materials import read_csv_bytes, MaterialError

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def write(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)

def main():
    edited = ['README.md', '.gitignore', 'docs/DEVELOPMENT_STATE.md', 'docs/SUBMISSION_READINESS.md',
              'submission/README.md', 'submission/PROJECT_DESCRIPTION.md', 'submission/PROJECT_DESCRIPTION.pdf',
              'submission/Описание проекта.pdf', 'submission/EXAMPLE.md', 'submission/TECHNICAL_APPENDIX.md',
              'submission/PUBLICATION_HANDOFF.md', 'submission/DEMO_RUNBOOK.md']
    for name in edited:
        source = ROOT/name
        target = HERE/'before'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        assert not target.exists()
        shutil.copyfile(source, target)
    protected = []
    for folder in ['projects', 'evaluation/task07/demo-workspace/projects',
                   'evaluation/provenance-release/continuation-workspace/projects']:
        protected.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    protected.extend((ROOT/'scripts').glob('*.py'))
    protected.extend((ROOT/'knowledge').rglob('*.md'))
    protected.append(ROOT/'AGENTS.md')
    protected.append(ROOT/'submission/video/Демонстрация.mp4')
    protected.extend(p for p in (ROOT/'dist').rglob('*.zip'))
    write(HERE/'preserved-before.json', {p.relative_to(ROOT).as_posix(): sha(p) for p in protected})
    candidates = list((ROOT/'online+shoppers+purchasing+intention+dataset').rglob('*.csv'))
    assert len(candidates) == 1, candidates
    path = candidates[0]
    raw = path.read_bytes()
    rows = list(csv.reader(io.StringIO(raw.decode('utf-8-sig'), newline=''), strict=True))
    headers, data = rows[0], rows[1:]
    report = {'at': datetime.now(timezone.utc).isoformat(), 'path': path.relative_to(ROOT).as_posix(),
              'absolute_path': str(path), 'sha256': sha(path), 'bytes': len(raw), 'columns': headers,
              'column_count': len(headers), 'rows': len(data), 'row_widths': dict(Counter(map(len,data))),
              'empty_cells': sum(v == '' for row in data for v in row),
              'revenue': dict(Counter(row[headers.index('Revenue')] for row in data))}
    try:
        parsed = read_csv_bytes(raw)
        report['normal_import_parser'] = {'status': 'ok', 'rows': len(parsed['rows'])}
    except MaterialError as e:
        report['normal_import_parser'] = {'status': 'error', 'diagnostic': str(e)}
    write(HERE/'local-file-check.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
