"""Export sectioned Russian Markdown to a readable local PDF; no installs or network.

Use <!-- PAGE --> between logical pages. Screenshots are real image files supplied
in Markdown/HTML. [[SCREENSHOT: ...]] is a draft-only labelled placeholder.
Existing outputs are never overwritten. Section overflow remains visible and is
reported; the exporter never reduces font size to satisfy a page limit.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import html
import importlib.metadata
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import unquote

import fitz
import markdown

CSS = '''
body { font-family: sans-serif; font-size: 11.25pt; line-height: 1.24; color: #182f39; }
h1 { font-size: 24pt; line-height: 1.08; color: #145363; margin: 0 0 11pt 0; }
h2 { font-size: 17pt; line-height: 1.12; color: #145363; margin: 0 0 10pt 0; }
h3 { font-size: 12pt; color: #145363; margin: 10pt 0 6pt 0; }
p { margin: 0 0 7pt 0; }
table { border-collapse: collapse; width: 100%; font-size: 9.7pt; line-height: 1.18; margin: 7pt 0 9pt 0; }
th { background-color: #e8f1f3; text-align: left; }
td, th { border: 0.5pt solid #a5bec4; padding: 4pt; vertical-align: top; }
blockquote { border-left: 2.5pt solid #519da9; padding-left: 9pt; margin: 7pt 0; }
a { color: #176f86; text-decoration: underline; }
ul, ol { margin: 5pt 0 7pt 0; padding-left: 16pt; }
li { margin-bottom: 4pt; }
img { width: 490pt; }
div.figure { margin: 8pt 0; page-break-inside: avoid; }
div.caption { font-size: 9.5pt; line-height: 1.15; color: #526972; margin: 3pt 0 7pt 0; }
div.placeholder { border: 1pt solid #c4b17f; background-color: #faf7ef; color: #6a5a31;
    font-size: 10pt; line-height: 1.25; padding: 27pt 12pt; margin: 9pt 0; }
pre { font-size: 9pt; line-height: 1.15; white-space: pre-wrap; background-color: #f1f5f6; padding: 6pt; }
code { font-size: 9.5pt; }
'''

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def relative_link(raw, source, output):
    raw = html.unescape(raw)
    if not raw or raw.startswith('#') or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', raw):
        return raw
    name, sep, anchor = raw.partition('#')
    target = (source.parent / unquote(name)).resolve()
    return Path(os.path.relpath(target, output.parent)).as_posix() + (sep + anchor if sep else '')

def export(source, output, title, draft=False, max_pages=5, png_dir=None):
    source = source.resolve(); output = output.resolve()
    if output.exists():
        raise FileExistsError(f'Choose a new output: {output}')
    text = source.read_text(encoding='utf-8')
    if not draft and ('[[SCREENSHOT:' in text or 'РЕДАКТОРУ:' in text):
        raise ValueError('Final export still contains editorial comments or screenshot placeholders')
    sections = [s.strip() for s in re.split(r'<!--\s*PAGE\s*-->', text) if s.strip()]
    document = fitz.open(); section_reports = []
    media = fitz.paper_rect('a4')
    area = fitz.Rect(42, 38, media.width - 42, media.height - 47)
    for index, section in enumerate(sections, 1):
        section = re.sub(r'\[\[SCREENSHOT:\s*(.*?)\]\]',
            lambda m: '<div class="placeholder"><b>Черновик: место для настоящего кадра.</b><br/>'
                + html.escape(m.group(1)) + '<br/>Изображение пока не вставлено.</div>', section)
        body = markdown.markdown(section, extensions=['tables', 'fenced_code'])
        body = re.sub(r'href="([^"]*)"',
            lambda m: 'href="' + html.escape(relative_link(m.group(1), source, output), quote=True) + '"', body)
        story = fitz.Story(html=body, user_css=CSS, archive=fitz.Archive(str(source.parent)))
        def rectfn(page_number, filled):
            if page_number > 20:
                raise ValueError('Unexpected section overflow; inspect source and images')
            return media, area, None
        part = story.write_with_links(rectfn)
        first = len(document) + 1
        document.insert_pdf(part, links=True)
        section_reports.append({'section': index, 'first_page': first, 'page_count': len(part)})
        part.close()
    for i, page in enumerate(document):
        footer = ('Черновик · ' if draft else '') + f'{i+1} / {len(document)}'
        page.insert_htmlbox(fitz.Rect(42, media.height - 32, media.width - 42, media.height - 14),
            '<p style="text-align:right; font-family:sans-serif; font-size:9pt; color:#617881">'
            + footer + '</p>')
    document.set_metadata({'title': title, 'subject': 'Описание проекта и подтверждённые границы',
        'creator': 'Local Markdown/PyMuPDF exporter', 'author': 'Команда проекта'})
    output.parent.mkdir(parents=True, exist_ok=True)
    document.save(output, garbage=4, deflate=True)
    report = {'observed_at': datetime.now(timezone.utc).isoformat(), 'source': str(source),
        'source_sha256': digest(source), 'output': str(output), 'output_sha256': digest(output),
        'draft': draft, 'pages': len(document), 'page_limit': max_pages,
        'page_limit_pass': len(document) <= max_pages, 'body_font_pt': 11.25,
        'sections': section_reports, 'links': [], 'broken_local_links': [], 'images': [],
        'versions': {n: importlib.metadata.version(n) for n in ('Markdown', 'PyMuPDF')}}
    for page_id, page in enumerate(document, 1):
        for link in page.get_links():
            record = {'page': page_id, 'kind': link['kind'],
                'uri': link.get('uri'), 'file': link.get('file'), 'target_page': link.get('page')}
            report['links'].append(record)
            target = link.get('file') or link.get('uri') or ''
            if target and not target.startswith('#') and not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target):
                target = unquote(target.split('#')[0])
                if not (output.parent / target).exists():
                    report['broken_local_links'].append({'page': page_id, 'target': target})
        if png_dir:
            png_dir.mkdir(parents=True, exist_ok=True)
            target = png_dir / f'page-{page_id:02}.png'
            if target.exists(): raise FileExistsError(target)
            page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).save(target)
            report['images'].append({'page': page_id, 'path': str(target), 'sha256': digest(target)})
    report_path = output.with_suffix('.inspection.json')
    with report_path.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    document.close()
    print(json.dumps({k:v for k,v in report.items() if k not in ('links','images')}, ensure_ascii=False))
    return report

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--title', default='Стратег Фабрики продуктов')
    parser.add_argument('--draft', action='store_true')
    parser.add_argument('--max-pages', type=int, default=5)
    parser.add_argument('--png-dir', type=Path)
    args = parser.parse_args()
    result = export(args.source, args.output, args.title, args.draft, args.max_pages, args.png_dir)
    sys.exit(0 if result['page_limit_pass'] and not result['broken_local_links'] else 1)
