"""Запускает новый codex exec с имеющейся авторизацией и сохраняет наблюдение.

Не меняет конфигурацию/права/auth. Технический timeout ограничивает зависший
процесс проверки, не исследование продукта. Не использует resume/fork.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--workspace', type=Path, required=True)
    p.add_argument('--request', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--timeout', type=int, default=600, help='Таймаут отсутствия нового вывода, не лимит всей работы')
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    request = a.request.read_text(encoding='utf-8').strip()
    cmd = [shutil.which('codex') or 'codex', 'exec', '--cd', str(a.workspace.resolve()), '--sandbox', 'workspace-write', '--skip-git-repo-check', '--ephemeral', '--json', '--color', 'never', '--output-last-message', str((a.output / 'last-message.txt').resolve()), request]
    started = datetime.now(timezone.utc).isoformat(); tick = time.monotonic()
    launch = {'started_at': started, 'request': request, 'argv': cmd, 'new_session': True, 'prior_transcript_supplied': False, 'inactivity_timeout_seconds': a.timeout}
    (a.output / 'launch.json').write_text(json.dumps(launch, ensure_ascii=False, indent=2), encoding='utf-8')
    with (a.output / 'events.jsonl').open('wb') as out, (a.output / 'stderr.txt').open('wb') as err:
        try:
            proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=out, stderr=err, cwd=a.workspace.resolve())
            launch['pid'] = proc.pid
            (a.output / 'launch.json').write_text(json.dumps(launch, ensure_ascii=False, indent=2), encoding='utf-8')
            last_activity = time.monotonic(); last_size = 0
            while proc.poll() is None:
                size = sum((a.output / f).stat().st_size for f in ('events.jsonl', 'stderr.txt'))
                if size != last_size:
                    last_size = size; last_activity = time.monotonic()
                if b'os error 10013' in (a.output / 'stderr.txt').read_bytes():
                    proc.terminate(); outcome = 'network_permission_error'; break
                if time.monotonic() - last_activity > a.timeout:
                    proc.terminate(); outcome = 'inactivity_timeout'; break
                time.sleep(1)
            else:
                outcome = 'exited'
            code = proc.wait(timeout=15)
        except OSError as exc:
            code = None; outcome = type(exc).__name__
    launch.update({'ended_at': datetime.now(timezone.utc).isoformat(), 'elapsed_seconds': round(time.monotonic()-tick, 3), 'exit_code': code, 'outcome': outcome})
    (a.output / 'outcome.json').write_text(json.dumps(launch, ensure_ascii=False, indent=2), encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(launch, ensure_ascii=False, indent=2))
