"""Локальная проверка неизменности страниц и перенос ссылок; не runtime агента."""
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import unquote
import argparse
import hashlib
import json
import os

import fitz

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare(before, after):
    with fitz.open(before) as old, fitz.open(after) as new:
        assert len(old) == len(new) == 5
        equal = [a.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).samples
                 == b.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).samples
                 for a, b in zip(old, new)]
        assert all(equal), 'Изменилось изображение страницы'
        return equal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--proof', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--extracted', type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    report = {'at': datetime.now(timezone.utc).isoformat(), 'source_sha256': digest(source),
              'before_sha256': digest(args.before), 'page_pixels_match': compare(args.before, source),
              'renderer': fitz.VersionBind, 'scale': 1.5}
    if args.output:
        assert args.extracted and not args.output.exists()
        output = args.output.resolve()
        with fitz.open(source) as document:
            for page in document:
                for link in page.get_links():
                    xref = link['xref']
                    if document.xref_get_key(xref, 'A/S') != ('name', '/Launch'):
                        continue
                    target = (source.parent / unquote(link['file'])).resolve()
                    relative = target.relative_to(ROOT)
                    delivered = args.extracted.resolve() / relative
                    assert delivered.is_file(), delivered
                    file_name = Path(os.path.relpath(delivered, output.parent)).as_posix()
                    for key in ('A/F/F', 'A/F/UF'):
                        document.xref_set_key(xref, key, fitz.get_pdf_str(file_name))
            output.parent.mkdir(parents=True, exist_ok=True)
            document.save(output, garbage=4, deflate=True)
        report.update(output_sha256=digest(output), relocated_pixels_match=compare(source, output))
    report['passed'] = True
    args.proof.parent.mkdir(parents=True, exist_ok=True)
    with args.proof.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
