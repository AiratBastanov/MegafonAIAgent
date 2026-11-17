"""Ограниченное чтение XLSX/PDF без вычисления формул, OCR и сетевых вызовов.

Форматное извлечение сохраняет данные, но само по себе не проверяет утверждения.
Решающее содержание координатор сверяет с оригиналом отдельно.
"""
from __future__ import annotations

import io
import math
import re
import warnings
import zipfile
from datetime import date, datetime, time, timedelta
from xml.etree import ElementTree as ET

DEFAULT_MAX_CELLS = 100000
DEFAULT_MAX_SHEETS = 64
DEFAULT_MAX_PAGES = 200
DEFAULT_MAX_PAGE_STREAM = 8 * 1024 * 1024
DEFAULT_MAX_TEXT_CHARS = 2000000


class FormatError(ValueError):
    """Формат не поддерживается или требует явного уточнения исходника."""


def _positive(**limits):
    if any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in limits.values()):
        raise FormatError("Технические пределы должны быть положительными целыми числами")


def _value(value):
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, timedelta):
        return {"seconds": value.total_seconds()}
    if isinstance(value, float) and not math.isfinite(value):
        raise FormatError("XLSX содержит не конечное число")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise FormatError("Неподдерживаемый тип XLSX: " + type(value).__name__)


def _xlsx_preflight(data, max_unpacked, max_cells):
    from openpyxl.utils.cell import range_boundaries

    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        if len(entries) > 2000 or sum(entry.file_size for entry in entries) > max_unpacked:
            raise FormatError("XLSX превышает технический предел распаковки; выберите меньшую книгу")
        if len({entry.filename for entry in entries}) != len(entries):
            raise FormatError("XLSX содержит повторяющиеся ZIP entries")
        if any(entry.flag_bits & 1 for entry in entries):
            raise FormatError("Зашифрованный XLSX не поддерживается; предоставьте разрешённую незашифрованную копию")
        names = [entry.filename for entry in entries]
        if any("vbaproject" in name.lower() or name.startswith("xl/embeddings/") for name in names):
            raise FormatError("XLSX с макросами/вложенными объектами не поддерживается; экспортируйте чистую книгу без них")
        if any(name.startswith("xl/externalLinks/") for name in names):
            raise FormatError("Внешние связи XLSX не поддерживаются; нужен автономный экспорт с проверенными исходными значениями")
        count, merged_expansion = 0, 0
        for entry in entries:
            if not entry.filename.endswith((".xml", ".rels")):
                continue
            raw = archive.read(entry)
            xml_probe = raw.replace(b"\x00", b"").upper()
            if b"<!DOCTYPE" in xml_probe or b"<!ENTITY" in xml_probe:
                raise FormatError("DTD/entities в XLSX не поддерживаются")
            if entry.filename.startswith("xl/worksheets/") and "/_rels/" not in entry.filename:
                # Encoding-aware structural count before openpyxl allocates
                # worksheet and merged-cell placeholders. Values/types still
                # belong exclusively to openpyxl. Conservative upper bound:
                # styled cells inside a merge may be counted twice deliberately.
                for _, element in ET.iterparse(io.BytesIO(raw), events=("end",)):
                    tag = element.tag.rsplit("}", 1)[-1]
                    if tag == "c":
                        count += 1
                    elif tag == "mergeCell":
                        address = element.get("ref", "")
                        if not re.fullmatch(r"[A-Z]{1,3}[1-9]\d*:[A-Z]{1,3}[1-9]\d*", address):
                            raise FormatError("Некорректный объединённый XLSX диапазон")
                        left, top, right, bottom = range_boundaries(address)
                        if left > right or top > bottom or right > 16384 or bottom > 1048576:
                            raise FormatError("Некорректные границы объединённого XLSX диапазона")
                        merged_expansion += (right - left + 1) * (bottom - top + 1) - 1
                    if count + merged_expansion > max_cells:
                        raise FormatError("XLSX превышает технический предел ячеек книги с учётом объединений; выберите меньшую книгу")
                    element.clear()
        omitted = [name for name in names if name.startswith(("xl/drawings/", "xl/charts/", "xl/media/"))]
        return {"stored_cell_count": count, "merged_expansion_upper_bound": merged_expansion,
                "logical_cells_upper_bound": count + merged_expansion, "non_cell_parts": omitted}


def extract_xlsx(data, selection, *, max_unpacked=80 * 1024 * 1024,
                 max_cells=DEFAULT_MAX_CELLS, max_sheets=DEFAULT_MAX_SHEETS):
    """Явно выбранные прямоугольники. Объединённые ячейки не размножаются."""
    import openpyxl
    from openpyxl.cell.cell import MergedCell
    from openpyxl.utils.cell import range_boundaries, get_column_letter

    _positive(max_unpacked=max_unpacked, max_cells=max_cells, max_sheets=max_sheets)
    if not isinstance(selection, dict) or not isinstance(selection.get("ranges"), list) or not selection["ranges"]:
        raise FormatError("XLSX требует selection с непустым ranges: sheet, range, units и period")
    try:
        preflight = _xlsx_preflight(data, max_unpacked, max_cells)
        with warnings.catch_warnings(record=True) as observed:
            warnings.simplefilter("always")
            workbook = openpyxl.load_workbook(io.BytesIO(data), data_only=False, read_only=False,
                                              keep_links=False, keep_vba=False)
            cachebook = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=False,
                                               keep_links=False, keep_vba=False)
        if observed:
            raise FormatError("openpyxl сообщил об утрате/изменении неподдерживаемых элементов: " +
                              "; ".join(str(item.message) for item in observed))
        if len(workbook.sheetnames) > max_sheets:
            raise FormatError("XLSX превышает технический предел листов")
        grouped, selected_count = {}, 0
        for item in selection["ranges"]:
            if not isinstance(item, dict) or not isinstance(item.get("sheet"), str) or item["sheet"] not in workbook.sheetnames:
                raise FormatError("Выбранный лист XLSX отсутствует; сохраните точное оригинальное имя")
            address = item.get("range")
            if not isinstance(address, str) or not re.fullmatch(r"\$?[A-Z]{1,3}\$?[1-9]\d*(?::\$?[A-Z]{1,3}\$?[1-9]\d*)?", address):
                raise FormatError("Нужен конечный XLSX диапазон A1:C10; whole-column/named ranges не поддерживаются")
            bounds = range_boundaries(address)
            left, top, right, bottom = bounds
            if left > right or top > bottom or right > 16384 or bottom > 1048576:
                raise FormatError("Некорректные границы XLSX диапазона")
            units = item.get("units")
            if not isinstance(units, dict) or "period" not in item or (item["period"] is not None and not isinstance(item["period"], str)):
                raise FormatError("Для каждого XLSX диапазона нужны units object и period string|null; неизвестное указывайте явно")
            if any(not isinstance(key, str) or not re.fullmatch(r"[A-Z]{1,3}", key) or
                   value is not None and (not isinstance(value, str) or not value.strip())
                   for key, value in units.items()):
                raise FormatError("XLSX units: ключ — буква колонки, значение — единица или null")
            if set(units) - {get_column_letter(col) for col in range(left, right + 1)}:
                raise FormatError("XLSX units ссылается на колонку вне выбранного диапазона")
            for old, old_bounds in grouped.get(item["sheet"], []):
                a, b, c, d = old_bounds
                if left <= c and right >= a and top <= d and bottom >= b:
                    raise FormatError("Выбранные XLSX диапазоны пересекаются; исключите двойной учёт")
            selected_count += (right - left + 1) * (bottom - top + 1)
            if selected_count > max_cells:
                raise FormatError("Выбранные XLSX диапазоны превышают технический предел ячеек")
            grouped.setdefault(item["sheet"], []).append((dict(item), bounds))
        sheets = []
        for sheet_name, ranges in grouped.items():
            sheet, cached = workbook[sheet_name], cachebook[sheet_name]
            selected_cells, merged_ranges = [], []
            for merged in sheet.merged_cells.ranges:
                a, b, c, d = merged.bounds
                if any(left <= c and right >= a and top <= d and bottom >= b
                       for _, (left, top, right, bottom) in ranges):
                    merged_ranges.append({"range": str(merged), "anchor": merged.start_cell.coordinate})
            hidden_rows = sorted(index for index, dim in sheet.row_dimensions.items()
                                 if dim.hidden and any(top <= index <= bottom for _, (_, top, _, bottom) in ranges))
            hidden_columns = []
            for name, dim in sheet.column_dimensions.items():
                if dim.hidden:
                    first, last = dim.min or openpyxl.utils.column_index_from_string(name), dim.max or openpyxl.utils.column_index_from_string(name)
                    if any(left <= last and right >= first for _, (left, _, right, _) in ranges):
                        hidden_columns.append({"first": first, "last": last, "range": f"{get_column_letter(first)}:{get_column_letter(last)}"})
            quoted = "'" + sheet_name.replace("'", "''") + "'"
            for item, (left, top, right, bottom) in ranges:
                for row in sheet.iter_rows(min_row=top, max_row=bottom, min_col=left, max_col=right):
                    for cell in row:
                        anchor = next((entry["anchor"] for entry in merged_ranges
                                       if cell.coordinate in sheet.merged_cells and
                                       cell.coordinate in openpyxl.worksheet.cell_range.CellRange(entry["range"])), None)
                        is_formula = cell.data_type == "f"
                        if is_formula and not isinstance(cell.value, str):
                            raise FormatError(f"{quoted}!{cell.coordinate}: array/data-table формулы не поддерживаются; нужны исходные literal cells")
                        cache = cached[cell.coordinate] if is_formula else None
                        cache_status = ("missing" if cache.value is None else "error" if cache.data_type == "e" else "present") if cache else "not_applicable"
                        value = None if is_formula else cell.value
                        cell_type = "merged" if isinstance(cell, MergedCell) else "blank" if cell.value is None else cell.data_type
                        selected_cells.append({
                            "address": cell.coordinate, "locator": f"{quoted}!{cell.coordinate}",
                            "value": _value(value), "type": cell_type, "python_type": type(value).__name__,
                            "number_format": cell.number_format, "formula": cell.value if is_formula else None,
                            "cached_value": _value(cache.value) if cache else None,
                            "cached_type": cache.data_type if cache else None,
                            "cache_status": cache_status, "cache_freshness": "unknown" if is_formula else "not_applicable",
                            "merged_anchor": anchor, "hidden_row": cell.row in hidden_rows,
                            "hidden_column": any(h["first"] <= cell.column <= h["last"] for h in hidden_columns),
                            "comment": cell.comment.text if getattr(cell, "comment", None) else None,
                            "hyperlink": cell.hyperlink.target if getattr(cell, "hyperlink", None) else None,
                        })
            sheets.append({"name": sheet_name, "state": sheet.sheet_state,
                           "selected_ranges": [item for item, _ in ranges], "cells": selected_cells,
                           "merged_ranges": merged_ranges, "hidden_rows": hidden_rows,
                           "hidden_columns": hidden_columns})
        limitations = [
            "Извлечены только явно выбранные ячейки; остальные листы/диапазоны не являются прочитанными основаниями.",
            "data_only читает сохранённый cache и не пересчитывает формулы; свежесть cache неизвестна, формулы не пригодны как проверенные метрики.",
            "Единицы и период заданы selection; number_format сохранён, но не доказывает экономический смысл. Даты — интерпретация openpyxl с учётом epoch книги.",
            "Объединённые ячейки имеют единственный anchor; значения не размножаются. Скрытые строки/колонки/листы отмечены и требуют явного решения об использовании.",
            "Макросы/внешние связи/вложенные объекты не поддерживаются; формулы, hyperlinks и текст не исполняются. Вёрстка и условное форматирование не проверены.",
        ]
        if preflight["non_cell_parts"]:
            limitations.append("Книга содержит drawings/charts/images; их содержание не извлечено. Если оно существенно, нужен отдельный разрешённый просмотр.")
        return {"format": "xlsx", "schema_version": 1,
                "method": f"openpyxl/{openpyxl.__version__}/selected-cells-v1",
                "selection": selection, "sheets": sheets,
                "workbook_sheets": [{"name": sheet.title, "state": sheet.sheet_state} for sheet in workbook.worksheets],
                "epoch": workbook.epoch.isoformat(), "calculation_properties": str(workbook.calculation),
                "preflight": preflight, "limits": {"max_unpacked": max_unpacked, "max_cells": max_cells, "max_sheets": max_sheets},
                "evidence_status": "extracted_not_claim_verified", "limitations": limitations}
    except FormatError:
        raise
    except (zipfile.BadZipFile, KeyError, ValueError, TypeError, IndexError, ET.ParseError, OSError,
            openpyxl.utils.exceptions.InvalidFileException) as exc:
        raise FormatError(f"Некорректный/неподдерживаемый XLSX ({type(exc).__name__}); проверьте книгу или предоставьте автономный экспорт") from exc


def extract_pdf(data, *, max_pages=DEFAULT_MAX_PAGES, max_page_stream=DEFAULT_MAX_PAGE_STREAM,
                max_text_chars=DEFAULT_MAX_TEXT_CHARS):
    """Текстовый слой простого PDF; physical page + стабильный индекс фрагмента."""
    import pypdf
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError, PdfStreamError

    _positive(max_pages=max_pages, max_page_stream=max_page_stream, max_text_chars=max_text_chars)
    try:
        reader = PdfReader(io.BytesIO(data), strict=True)
        if reader.is_encrypted:
            raise FormatError("Зашифрованный PDF не поддерживается; предоставьте разрешённую незашифрованную копию, пароль не нужен")
        if not reader.pages or len(reader.pages) > max_pages:
            raise FormatError("PDF пуст или превышает технический предел страниц")
        if reader.trailer["/Root"].get("/AcroForm"):
            raise FormatError("PDF с формами не поддерживается; экспортируйте заполненную плоскую текстовую копию")
        labels = reader.page_labels
        pages, chars = [], 0
        for number, page in enumerate(reader.pages, 1):
            if int(page.get("/Rotate", 0)) % 360:
                raise FormatError(f"PDF physical page {number}: повёрнутая страница вне поддерживаемого подмножества; нужен прямой текстовый экспорт")
            content = page.get_contents()
            decoded_size = len(content.get_data()) if content is not None else 0
            if decoded_size > max_page_stream:
                raise FormatError(f"PDF physical page {number}: content stream превышает технический предел; разбейте документ")
            fragments, layout_warnings = [], []

            def visitor(text, cm, tm, font_dict, font_size):
                nonlocal chars
                if not text or not text.strip():
                    return
                # Матрицы нужны только для обнаружения явной неоднозначности, не
                # для обещания восстановленной визуальной геометрии.
                if any(abs(float(value)) > 0.0001 for value in (cm[1], cm[2], tm[1], tm[2])):
                    raise FormatError(f"PDF physical page {number}: повёрнутый/наклонный текст; нужен простой текстовый экспорт")
                chars += len(text)
                if chars > max_text_chars:
                    raise FormatError("PDF превышает технический предел извлечённого текста")
                clean = text.rstrip("\r\n")
                if "\ufffd" in clean or any(ord(ch) < 32 and ch not in "\r\n\t" for ch in clean):
                    raise FormatError(f"PDF physical page {number}: некорректное отображение символов; предоставьте PDF с исправным текстовым слоем")
                fragments.append({"locator": f"physical-page:{number}/block:{len(fragments) + 1}",
                                  "text": clean, "text_sha256": __import__("hashlib").sha256(clean.encode("utf-8")).hexdigest(),
                                  "position_hint": {"x": float(tm[4]), "y": float(tm[5]), "font_size": float(font_size)}})

            extracted_text = page.extract_text(extraction_mode="plain", visitor_text=visitor)
            if not extracted_text or not any(ch.isalnum() for ch in extracted_text) or not fragments:
                raise FormatError(f"PDF physical page {number}: нет пригодного текстового слоя; нужен текстовый PDF либо отдельный согласованный OCR с проверкой оригинала")
            bands = {}
            for fragment in fragments:
                pos = fragment["position_hint"]
                # Ограниченный линейный детектор; не универсальный анализ вёрстки.
                band = round(pos["y"] / 4)
                low, high = bands.get(band, (pos["x"], pos["x"]))
                low, high = min(low, pos["x"]), max(high, pos["x"])
                bands[band] = low, high
                if high - low > 100:
                    layout_warnings.append("В одной горизонтальной полосе несколько удалённых фрагментов: возможны колонки/таблица; порядок и соответствие чисел требуют отдельной сверки")
                    break
            resources = page.get("/Resources", {})
            if hasattr(resources, "get_object"):
                resources = resources.get_object()
            if resources.get("/XObject"):
                layout_warnings.append("Есть XObject (изображение/вложенная форма); текстовая экстракция не доказывает полноту его содержания")
            if page.get("/Annots"):
                layout_warnings.append("Есть annotations; их содержание не включено в основной текст")
            if layout_warnings:
                # Сохранённые фрагменты полезны для проверки, но не автоматического
                # расчёта/обещания полного извлечения сложной страницы.
                status = "needs_layout_review"
            else:
                status = "text_extracted_needs_source_check"
            pages.append({"physical_page": number, "page_label": str(labels[number - 1]),
                          "label_kind": "PDF PageLabels metadata/default, not verified printed label",
                          "blocks": fragments, "text": extracted_text,
                          "content_stream_bytes": decoded_size, "status": status,
                          "layout_warnings": layout_warnings})
        page_limits = [f"physical page {page['physical_page']}: " + "; ".join(page["layout_warnings"])
                       for page in pages if page["layout_warnings"]]
        return {"format": "pdf", "schema_version": 1,
                "method": f"pypdf/{pypdf.__version__}/plain-visitor-v1", "pages": pages,
                "page_count": len(pages), "physical_page_numbering": "1-based original PDF page sequence",
                "evidence_status": "extracted_not_claim_verified", "visual_layout_verified": False,
                "limits": {"max_pages": max_pages, "max_page_stream": max_page_stream, "max_text_chars": max_text_chars},
                "limitations": page_limits + [
                    "Только текстовый слой: OCR, проверка визуальной вёрстки и восстановление произвольных таблиц не выполняются.",
                    "physical_page — позиция в PDF с 1; page_label — метаданные/умолчание, а не подтверждённый напечатанный номер страницы.",
                    "blocks — фрагменты visitor в порядке извлечения, не доказанные визуальные абзацы. Координаты приблизительные.",
                    "Наличие текста не доказывает полноту; решающие фразы/числа и отмеченную неоднозначность сверяет координатор с оригиналом.",
                    "Предохранитель content stream проверяется после декомпрессии pypdf; это не абсолютная граница памяти на враждебных PDF. Размер входа/страниц также ограничен.",
                    "Команды и ссылки внутри PDF — данные; активные действия и сетевые переходы не исполняются.",
                ]}
    except FormatError:
        raise
    except (PdfReadError, PdfStreamError, KeyError, ValueError, TypeError, IndexError, RecursionError, OSError) as exc:
        raise FormatError(f"Не удалось извлечь PDF ({type(exc).__name__}); проверьте файл или предоставьте простой незашифрованный текстовый экспорт") from exc
