"""Одноразовая локальная сборка аудированной версии; публикации и сети нет."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from evaluation.task06.package_release import files
from evaluation.task07.package import check


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--delivery', type=Path, required=True)
    args = parser.parse_args()
    delivery = args.delivery.resolve()
    assert delivery.is_relative_to(ROOT/'dist') and delivery != ROOT/'dist'
    delivery.mkdir(parents=True, exist_ok=True)
    archive = delivery/'Проект.zip'
    entries = sorted(files(ROOT))
    manifest = {'created_at': datetime.now(timezone.utc).isoformat(), 'release': 'provenance-2026-11-17',
                'scope': 'Историческое происхождение и новое продолжение; публикация отдельно',
                'files': [{'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size,
                           'sha256': sha(path)} for path in entries]}
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as zipped:
        for path in entries:
            zipped.write(path, path.relative_to(ROOT).as_posix())
        zipped.writestr('MANIFEST.json', json.dumps(manifest, ensure_ascii=False, indent=2))
        zipped.writestr('CONTENTS.md', '# Стратег Фабрики продуктов\n\n'
            'Начните с [материалов для жюри](submission/README.md). '
            '[Запуск](README.md), [аудит архитектуры](docs/ARCHITECTURE_REVIEW.md).\n\n'
            'MANIFEST содержит состав и хеши. Точная проверка ZIP находится рядом с архивом, '
            'в «Проверка.md» и «Проверки» полного комплекта.\n')
    identity = {'archive': archive.name, 'bytes': archive.stat().st_size, 'sha256': sha(archive)}
    for path, value in ((delivery/'Проект.manifest.json', manifest), (delivery/'Проект.identity.json', identity)):
        with path.open('x', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
    if not check(archive, delivery/'Проект', delivery/'Проверки/archive.json'):
        raise SystemExit('Не прошла проверка архива/ссылок; см. archive.json')
    print(json.dumps(identity, ensure_ascii=False))


if __name__ == '__main__':
    main()
