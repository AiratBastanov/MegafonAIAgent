"""Малый capture subprocess: generic tools, без ответов/модели/сети."""
from pathlib import Path
from datetime import datetime, timezone
import json
import os
import subprocess
import sys
import time


def main():
    # python capture.py LOG_DIR LABEL -- EXECUTABLE ARG...
    folder = Path(sys.argv[1]) / sys.argv[2]
    command = sys.argv[4:] if sys.argv[3] == '--' else sys.argv[3:]
    folder.mkdir(parents=True, exist_ok=False)
    start = datetime.now(timezone.utc).isoformat()
    counter = time.monotonic()
    result = subprocess.run(command, capture_output=True, encoding='utf-8', errors='replace',
                            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}, timeout=180)
    end = datetime.now(timezone.utc).isoformat()
    (folder / 'stdout.txt').write_text(result.stdout, encoding='utf-8')
    (folder / 'stderr.txt').write_text(result.stderr, encoding='utf-8')
    (folder / 'result.json').write_text(json.dumps(dict(command=command, cwd=str(Path.cwd()),
        started_at=start, ended_at=end, elapsed_seconds=time.monotonic()-counter,
        returncode=result.returncode), ensure_ascii=False, indent=2), encoding='utf-8')
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())
