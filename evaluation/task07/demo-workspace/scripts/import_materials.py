"""Register permitted, project-local materials without interpreting embedded instructions.

Supports small declared DOCX/XLSX/text-layer PDF subsets, UTF-8 CSV/text and web excerpts.
The coordinator obtains web pages; this utility never opens a network connection.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

VERSION = "2.0"
DEFAULT_MAX_BYTES = 20 * 1024 * 1024
DEFAULT_MAX_UNPACKED = 80 * 1024 * 1024
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class MaterialError(ValueError):
    """Input is invalid, unsupported, or outside the intended project."""


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def scoped(project, path, *, must_exist=True):
    root = Path(project).resolve(strict=True)
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve(strict=must_exist)
    if not resolved.is_relative_to(root) or resolved == root:
        raise MaterialError("Путь должен находиться внутри выбранного проекта")
    # resolve follows symlinks and junctions, including existing parent directories.
    return resolved


def relative(project, path):
    return Path(path).resolve().relative_to(Path(project).resolve()).as_posix()


def write_new(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(content)


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def read_csv_bytes(data, *, delimiter=",", max_rows=50000):
    if len(delimiter) != 1:
        raise MaterialError("Разделитель CSV должен состоять из одного символа")
    try:
        reader = csv.reader(io.StringIO(data.decode("utf-8-sig"), newline=""),
                            delimiter=delimiter, strict=True)
        columns = next(reader)
        if not columns or any(not c or c.strip() != c for c in columns):
            raise MaterialError("Пустые имена или пробелы вокруг имён колонок")
        if len(set(columns)) != len(columns):
            raise MaterialError("Повторяющиеся колонки CSV")
        rows = []
        last_line = reader.line_num
        for index, values in enumerate(reader, 1):
            start = last_line + 1
            last_line = reader.line_num
            if len(values) != len(columns):
                raise MaterialError(f"CSV: строка {start}, число полей не совпадает с заголовком")
            if index > max_rows:
                raise MaterialError("CSV превышает технический предел строк")
            rows.append({"locator": f"rows:{start}-{last_line}", "record": index,
                         "line_start": start, "line_end": last_line,
                         "values": dict(zip(columns, values))})
        if not rows:
            raise MaterialError("CSV не содержит записей")
        return {"columns": columns, "rows": rows, "delimiter": delimiter,
                "encoding": "utf-8-sig", "row_locator": "physical lines, inclusive"}
    except (UnicodeError, csv.Error, StopIteration) as exc:
        raise MaterialError(f"Некорректный UTF-8 CSV: {type(exc).__name__}") from exc


def paragraph_text(element):
    parts = []
    for node in element.iter():
        if node.tag == W + "t":
            parts.append(node.text or "")
        elif node.tag == W + "tab":
            parts.append("\t")
        elif node.tag in {W + "br", W + "cr"}:
            parts.append("\n")
        elif node.tag == W + "noBreakHyphen":
            parts.append("\u2011")
        elif node.tag == W + "softHyphen":
            parts.append("\u00ad")
    return "".join(parts)


def extract_docx(data, *, max_unpacked=DEFAULT_MAX_UNPACKED):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as package:
            entries = package.infolist()
            if len(entries) > 2000 or sum(x.file_size for x in entries) > max_unpacked:
                raise MaterialError("DOCX превышает технический предел распаковки")
            if len({x.filename for x in entries}) != len(entries):
                raise MaterialError("DOCX содержит повторяющиеся ZIP entries")
            if any(x.flag_bits & 1 for x in entries):
                raise MaterialError("Зашифрованный DOCX не поддерживается")
            if any(x.filename.startswith("word/embeddings/") or "vbaProject" in x.filename for x in entries):
                raise MaterialError("Вложенные объекты/макросы не поддерживаются")
            xml = package.read("word/document.xml")
            if b"<!DOCTYPE" in xml.upper() or b"<!ENTITY" in xml.upper():
                raise MaterialError("DTD/entities в DOCX не поддерживаются")
            root = ET.fromstring(xml)
            unsupported = {W + name for name in
                           ("ins", "del", "drawing", "pict", "txbxContent", "altChunk",
                            "fldSimple", "instrText", "sdt", "gridSpan", "vMerge",
                            "moveFrom", "moveTo", "moveFromRangeStart", "moveFromRangeEnd",
                            "moveToRangeStart", "moveToRangeEnd")}
            found = sorted({node.tag.split("}")[-1] for node in root.iter()
                            if node.tag in unsupported})
            if found:
                raise MaterialError("Неподдерживаемые DOCX элементы: " + ", ".join(found))
            body = root.find(W + "body")
            if body is None:
                raise MaterialError("DOCX body отсутствует")
            blocks, p_index, t_index = [], 0, 0
            for element in body:
                if element.tag == W + "sectPr":
                    continue
                b_index = len(blocks) + 1
                if element.tag == W + "p":
                    p_index += 1
                    blocks.append({"kind": "paragraph", "locator": f"body/b{b_index}/p{p_index}",
                                   "text": paragraph_text(element)})
                elif element.tag == W + "tbl":
                    t_index += 1
                    if any(node is not element for node in element.iter(W + "tbl")):
                        raise MaterialError("Вложенные DOCX таблицы не поддерживаются")
                    table = {"kind": "table", "locator": f"body/b{b_index}/t{t_index}", "rows": []}
                    for r_index, row in enumerate(element.findall(W + "tr"), 1):
                        cells = []
                        for c_index, cell in enumerate(row.findall(W + "tc"), 1):
                            locator = f"{table['locator']}/r{r_index}/c{c_index}"
                            cells.append({"locator": locator, "paragraphs": [
                                {"locator": f"{locator}/p{i}", "text": paragraph_text(p)}
                                for i, p in enumerate(cell.findall(W + "p"), 1)]})
                        table["rows"].append(cells)
                    blocks.append(table)
                else:
                    raise MaterialError("Неподдерживаемый DOCX body блок: " + element.tag.split("}")[-1])
            limitations = ["Только body и простые таблицы; номера страниц не определяются; вёрстка и оформление не анализируются."]
            omitted = [x.filename for x in entries if re.match(r"word/(header|footer|footnotes|endnotes|comments).*\.xml$", x.filename)]
            if omitted:
                raise MaterialError("DOCX содержит отдельные текстовые части вне body: " + ", ".join(omitted))
            return {"blocks": blocks, "limitations": limitations}
    except (zipfile.BadZipFile, KeyError, ET.ParseError, RuntimeError) as exc:
        raise MaterialError(f"Некорректный DOCX: {type(exc).__name__}") from exc


def validate_time(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError()
    except (ValueError, AttributeError) as exc:
        raise MaterialError("Время должно быть ISO 8601 с часовым поясом") from exc


def register(project, source_id, input_path, kind, *, origin=None, synthetic=False,
             accessed_at=None, locator=None, limitations=None, retrieval_status=None,
             delimiter=",", max_bytes=DEFAULT_MAX_BYTES, max_unpacked=DEFAULT_MAX_UNPACKED,
             max_rows=50000, selection_path=None, max_cells=100000, max_sheets=64,
             max_pages=200, max_page_stream=8 * 1024 * 1024, max_text_chars=2000000):
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", source_id):
        raise MaterialError("Недопустимый source ID")
    if kind not in {"docx", "csv", "text", "web-excerpt", "xlsx", "pdf"}:
        raise MaterialError("Неподдерживаемый формат")
    if selection_path is not None and kind != "xlsx":
        raise MaterialError("--selection поддерживается только для XLSX")
    if max_bytes <= 0 or max_unpacked <= 0 or max_rows <= 0:
        raise MaterialError("Технические пределы должны быть положительными")
    incoming = scoped(project, input_path)
    if incoming.stat().st_size > max_bytes:
        raise MaterialError("Файл превышает технический предел размера")
    data = incoming.read_bytes()
    origin = origin or relative(project, incoming)
    if kind == "web-excerpt":
        from urllib.parse import urlparse
        parsed = urlparse(origin)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise MaterialError("Нужен публичный URL без credentials")
        if not accessed_at or not locator or retrieval_status not in {"current_host_read", "supplied_snapshot"}:
            raise MaterialError("Web: нужны время доступа, locator и retrieval_status")
        validate_time(accessed_at)
    elif accessed_at:
        validate_time(accessed_at)
    if kind == "docx":
        extracted = extract_docx(data, max_unpacked=max_unpacked)
        method = "stdlib.zipfile+ElementTree/simple-docx-body-v2"
    elif kind == "csv":
        extracted = read_csv_bytes(data, delimiter=delimiter, max_rows=max_rows)
        method = "stdlib.csv/strict-utf8-v1"
    elif kind in {"xlsx", "pdf"}:
        try:
            try:
                from .extract_formats import extract_xlsx, extract_pdf, FormatError
            except ImportError:
                from extract_formats import extract_xlsx, extract_pdf, FormatError
            if kind == "xlsx":
                if not selection_path:
                    raise MaterialError("XLSX требует --selection с явными sheet/range/units/period")
                selection_file = scoped(project, selection_path)
                if selection_file.stat().st_size > max_bytes:
                    raise MaterialError("XLSX selection превышает технический предел размера")
                selection_bytes = selection_file.read_bytes()
                selection = json.loads(selection_bytes.decode("utf-8-sig"))
                extracted = extract_xlsx(data, selection, max_unpacked=max_unpacked,
                                         max_cells=max_cells, max_sheets=max_sheets)
            else:
                if selection_path is not None:
                    raise MaterialError("--selection поддерживается только для XLSX")
                extracted = extract_pdf(data, max_pages=max_pages, max_page_stream=max_page_stream,
                                        max_text_chars=max_text_chars)
            method = extracted["method"]
        except ImportError as exc:
            raise MaterialError("Для XLSX/PDF установите зависимости requirements.txt в локальную .venv") from exc
        except FormatError as exc:
            raise MaterialError(str(exc)) from exc
    else:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeError as exc:
            raise MaterialError("Текст должен быть UTF-8") from exc
        extracted = {"lines": [{"locator": f"line:{i}", "text": line}
                               for i, line in enumerate(text.splitlines(), 1)]}
        method = "host-rendered-excerpt/utf8-registration-v1" if kind == "web-excerpt" else "utf8-lines-v1"
    limitations = list(limitations or []) + extracted.get("limitations", [])
    if kind == "web-excerpt":
        limitations.append("Сохранена ограниченная выдержка представления хоста, не оригинальный HTML; инструмент не подтверждает текущую доступность URL.")
    identity = {"id": source_id, "kind": kind, "origin": origin,
                "input_sha256": sha256(data), "synthetic": bool(synthetic),
                "accessed_at": accessed_at, "locator": locator,
                "retrieval_status": retrieval_status or "local_import",
                "extraction_method": method, "limitations": limitations,
                "delimiter": delimiter if kind == "csv" else None}
    if kind == "xlsx":
        identity.update({"selection": selection,
                         "selection_input": {"path": relative(project, selection_file), "sha256": sha256(selection_bytes)}})
    folder = scoped(project, f"evidence/sources/{source_id}", must_exist=False)
    version_dirs = [p for p in folder.glob("v*") if re.fullmatch(r"v\d+", p.name)] if folder.exists() else []
    # Check each discovered directory before probing or reading metadata. A vN
    # symlink/junction is untrusted even though its parent directory is scoped.
    for version_path in version_dirs:
        scoped(project, version_path)
    incomplete = [relative(project, p) for p in version_dirs if not (p / "source.json").is_file()]
    versions = sorted((p / "source.json" for p in version_dirs if (p / "source.json").is_file()),
                      key=lambda p: int(p.parent.name[1:]))
    for meta_path in reversed(versions):
        try:
            meta_path = scoped(project, meta_path)
            record = json.loads(meta_path.read_text(encoding="utf-8"))
            if not isinstance(record, dict):
                raise MaterialError("Некорректная предыдущая регистрация: требуется JSON object")
            # A changed import policy/provenance is a meaningful revision even with identical bytes.
            if all(record.get(k) == v for k, v in identity.items()):
                for ref_name in ("original", "extract"):
                    ref = record[ref_name]
                    if sha256(scoped(project, ref["path"]).read_bytes()) != ref["sha256"]:
                        raise MaterialError("Повреждён ранее зарегистрированный источник")
                return {"reused": True, "source": record, "incomplete_versions": incomplete,
                        "record": {"path": relative(project, meta_path), "sha256": sha256(meta_path.read_bytes())}}
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            raise MaterialError("Некорректная предыдущая регистрация источника") from exc
    existing_numbers = [int(p.name[1:]) for p in folder.glob("v*") if re.fullmatch(r"v\d+", p.name)] if folder.exists() else []
    version = max(existing_numbers, default=0) + 1
    version_dir = scoped(project, folder / f"v{version}", must_exist=False)
    suffix = {"docx": ".docx", "csv": ".csv", "text": ".txt", "web-excerpt": ".txt", "xlsx": ".xlsx", "pdf": ".pdf"}[kind]
    original_path, extract_path = version_dir / ("original" + suffix), version_dir / "extract.json"
    extracted.update({"source_id": source_id, "source_version": version, "synthetic": bool(synthetic),
                      "source_kind": kind, "input_sha256": sha256(data), "extraction_method": method})
    extracted_bytes = json_bytes(extracted)
    record = {**identity, "version": version, "imported_at": utc_now(), "published_at": None,
              "input_path": relative(project, incoming), "tool_version": VERSION,
              "original": {"path": relative(project, original_path), "sha256": sha256(data)},
              "extract": {"path": relative(project, extract_path), "sha256": sha256(extracted_bytes)}}
    # Metadata is published last; incomplete directories are never accepted as registered results.
    write_new(original_path, data)
    write_new(extract_path, extracted_bytes)
    record_path, record_bytes = version_dir / "source.json", json_bytes(record)
    write_new(record_path, record_bytes)
    return {"reused": False, "source": record, "incomplete_versions": incomplete,
            "record": {"path": relative(project, record_path), "sha256": sha256(record_bytes)}}


def main():
    parser = argparse.ArgumentParser(description="Регистрация разрешённого локального источника; web читает хост")
    parser.add_argument("--project", required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--kind", required=True, choices=["docx", "csv", "text", "web-excerpt", "xlsx", "pdf"])
    parser.add_argument("--origin")
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--accessed-at")
    parser.add_argument("--locator")
    parser.add_argument("--limitations", action="append", default=[])
    parser.add_argument("--retrieval-status", choices=["current_host_read", "supplied_snapshot"])
    parser.add_argument("--delimiter", default=",")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument("--max-unpacked", type=int, default=DEFAULT_MAX_UNPACKED)
    parser.add_argument("--max-rows", type=int, default=50000)
    parser.add_argument("--selection", dest="selection_path", help="XLSX: проектный JSON ranges со sheet/range/units/period")
    parser.add_argument("--max-cells", type=int, default=100000)
    parser.add_argument("--max-sheets", type=int, default=64)
    parser.add_argument("--max-pages", type=int, default=200)
    parser.add_argument("--max-page-stream", type=int, default=8 * 1024 * 1024)
    parser.add_argument("--max-text-chars", type=int, default=2000000)
    args = vars(parser.parse_args())
    args["input_path"] = args.pop("input")
    try:
        result = register(**args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (MaterialError, OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
