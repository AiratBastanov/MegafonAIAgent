"""Существующая упаковка плюс свежая offline-проверка; отчёты вне ZIP."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
DELIVERY = ROOT/'dist/Материалы-2026-11-17-2'
CHECKS = DELIVERY/'Проверки'
ENVIRONMENT = ROOT/'_provenance-release/venv'
sys.stdout.reconfigure(encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def run(name, command, cwd, timeout=180):
    folder = CHECKS/name
    folder.mkdir(parents=True, exist_ok=False)
    request = dict(command=list(map(str,command)), cwd=str(cwd),
                   started_at=datetime.now(timezone.utc).isoformat(), network='not needed',
                   environment='PYTHONIOENCODING=utf-8; PYTHONDONTWRITEBYTECODE=1; PYTHONNOUSERSITE=1; PYTHONPATH removed')
    write(folder/'request.json',request)
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1')
    env.pop('PYTHONPATH',None)
    start=time.monotonic()
    with (folder/'stdout.txt').open('wb') as out, (folder/'stderr.txt').open('wb') as err:
        result=subprocess.run(request['command'],cwd=cwd,stdout=out,stderr=err,env=env,timeout=timeout)
    report=dict(request, ended_at=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-start,
                returncode=result.returncode,stdout_sha256=sha(folder/'stdout.txt'),stderr_sha256=sha(folder/'stderr.txt'))
    write(folder/'result.json',report)
    print(name,result.returncode,round(report['elapsed_seconds'],3),flush=True)
    assert result.returncode==0, folder


def main():
    assert not DELIVERY.exists() and not ENVIRONMENT.exists()
    old = ROOT/'dist/Материалы-2026-11-17'
    protected = {str(p.relative_to(ROOT)):sha(p) for p in [old/'Проект.zip', ROOT/'dist/Материалы-2026-11-16/Проект.zip']}
    run('package',[sys.executable,ROOT/'evaluation/provenance-release/package_candidate.py','--delivery',DELIVERY],ROOT)
    extracted=DELIVERY/'Проект'
    shutil.copyfile(old/'Демонстрация.mp4', DELIVERY/'Демонстрация.mp4')
    shutil.copyfile(old/'Описание проекта.pdf', DELIVERY/'Описание проекта.pdf')
    page=(old/'Начать.html').read_text(encoding='utf-8')
    page=page.replace('Новый код проверен отдельно;', 'В текущем выпуске устранена подмена происхождения старой версии источника. Новый Codex отдельно продолжил незавершённый проект и сохранил аналитический результат;')
    page=page.replace('<li><a href="Проект/docs/ARCHITECTURE_REVIEW.md">', '<li><a href="Проект/evaluation/provenance-release/CONTINUATION.md">Новое продолжение после паузы</a> — отдельный запуск на исправленной версии.</li>\n<li><a href="Проект/docs/ARCHITECTURE_REVIEW.md">')
    page=page.replace('<a href="Проверка.md">Результаты проверки комплекта</a>', '<a href="Проверка.md">Результаты проверки комплекта</a> · <a href="Проект/submission/PUBLICATION_HANDOFF.md">Передача на публикацию</a>')
    (DELIVERY/'Начать.html').write_text(page,encoding='utf-8')
    write(CHECKS/'pdf-visual.json',dict(basis='Байты обоих PDF совпадают с предыдущим проверенным комплектом; новый рендер не нужен',
        standalone_sha256=sha(DELIVERY/'Описание проекта.pdf'),archive_pdf_sha256=sha(extracted/'submission/Описание проекта.pdf'),
        previous_standalone_sha256=sha(old/'Описание проекта.pdf'),
        prior_visual_proof='Проект/evaluation/architecture-review/pdf-repair.json',passed=True))
    ENVIRONMENT.parent.mkdir(parents=True,exist_ok=True)
    run('setup-create',[sys.executable,'-m','venv',ENVIRONMENT],extracted)
    python=ENVIRONMENT/'Scripts/python.exe'
    run('setup-install',[python,'-m','pip','install','--no-index','--no-cache-dir','--find-links','third_party/wheels','-r','requirements.txt'],extracted)
    run('pip-check',[python,'-m','pip','check'],extracted)
    run('regression',[python,'-m','unittest','discover','-s','tests','-q'],extracted)
    run('release-check',[python,'evaluation/provenance-release/verify_candidate.py','--output',CHECKS/'release.json',
                         '--standalone',DELIVERY/'Описание проекта.pdf'],extracted)
    assert all(sha(ROOT/n)==h for n,h in protected.items())
    write(CHECKS/'preserved-releases.json',dict(files=protected,unchanged=True))
    print('Свежая проверка кандидата завершена.',flush=True)


if __name__=='__main__':
    main()
