"""Явные агрегаты CSV и literal-ячеек зарегистрированного XLSX; без eval."""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from collections import OrderedDict
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction
from pathlib import Path

try:
    from .import_materials import (MaterialError, DEFAULT_MAX_BYTES, json_bytes, read_csv_bytes,
                                   relative, scoped, sha256, utc_now, write_new)
except ImportError:
    from import_materials import (MaterialError, DEFAULT_MAX_BYTES, json_bytes, read_csv_bytes,
                                  relative, scoped, sha256, utc_now, write_new)

VERSION = "1.2"
MAX_NUMERIC_DIGITS = 18
MAX_NUMERIC_EXPONENT = 12


def decimal_value(value, name):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise MaterialError(f"Некорректное число: {name}") from exc
    if not result.is_finite():
        raise MaterialError(f"Не конечное число: {name}")
    if len(result.as_tuple().digits) > MAX_NUMERIC_DIGITS or abs(result.as_tuple().exponent) > MAX_NUMERIC_EXPONENT:
        raise MaterialError(f"Число превышает технический предел: {name}; до {MAX_NUMERIC_DIGITS} цифр коэффициента и |exponent| <= {MAX_NUMERIC_EXPONENT}")
    return result


def exact_sum(values):
    """Enough precision for every input digit and carry; no intermediate rounding."""
    values = list(values)
    if not values:
        return Decimal(0)
    places = max(v.adjusted() for v in values) - min(v.as_tuple().exponent for v in values) + 1
    with localcontext() as context:
        context.prec = max(28, places + len(str(len(values))) + 2)
        return sum(values, Decimal(0))


def rounded_value(numerator, denominator, multiplier, places):
    """Exact rational ROUND_HALF_UP avoids rounding a near-half ratio twice."""
    ratio = Fraction(numerator) / Fraction(denominator) * Fraction(multiplier)
    scaled_numerator = ratio.numerator * (10 ** places)
    whole, remainder = divmod(abs(scaled_numerator), ratio.denominator)
    if 2 * remainder >= ratio.denominator:
        whole += 1
    digits = str(whole).rjust(places + 1, "0")
    result = digits if places == 0 else digits[:-places] + "." + digits[-places:]
    return ("-" if scaled_numerator < 0 else "") + result


def validate_spec(spec, headers):
    if not isinstance(spec, dict):
        raise MaterialError("Спецификация должна быть JSON object")
    for required in ("columns", "group_by", "period_column", "metrics", "missing_values", "synthetic"):
        if required not in spec:
            raise MaterialError("В спецификации отсутствует " + required)
    columns, groups = spec["columns"], spec["group_by"]
    if not isinstance(columns, dict):
        raise MaterialError("columns должен быть JSON object")
    if set(columns) != set(headers):
        raise MaterialError("Колонки CSV и спецификации должны точно совпадать")
    if not isinstance(groups, list) or not groups or len(groups) != len(set(groups)) or not set(groups) <= set(columns):
        raise MaterialError("group_by должен перечислять известные уникальные колонки")
    if spec["period_column"] not in groups:
        raise MaterialError("period_column должен входить в group_by: периоды не смешиваются автоматически")
    if not isinstance(spec["synthetic"], bool):
        raise MaterialError("synthetic должен быть boolean")
    if not isinstance(spec["missing_values"], list) or any(not isinstance(x, str) for x in spec["missing_values"]):
        raise MaterialError("missing_values должен быть списком строк")
    for name, rule in columns.items():
        if not isinstance(rule, dict) or rule.get("type") not in {"text", "integer", "decimal"} or not rule.get("unit"):
            raise MaterialError(f"Для колонки {name} нужны type и unit")
    ids = []
    if not isinstance(spec["metrics"], list) or not spec["metrics"]:
        raise MaterialError("Нужна хотя бы одна метрика")
    for metric in spec["metrics"]:
        if not isinstance(metric, dict):
            raise MaterialError("Определение метрики должно быть JSON object")
        mid = metric.get("id")
        if not isinstance(mid, str) or not mid or mid in ids:
            raise MaterialError("ID метрик должны быть непустыми и уникальными")
        ids.append(mid)
        if metric.get("operation") not in {"sum", "ratio"} or not metric.get("unit"):
            raise MaterialError(f"{mid}: нужны operation=sum|ratio и unit")
        if not isinstance(metric.get("rounding"), int) or not 0 <= metric["rounding"] <= 10:
            raise MaterialError(f"{mid}: rounding должен быть от 0 до 10 знаков")
        for part in (["numerator", "denominator"] if metric["operation"] == "ratio" else ["numerator"]):
            names = metric.get(part)
            if not isinstance(names, list) or not names or len(names) != len(set(names)):
                raise MaterialError(f"{mid}: нужен непустой список уникальных колонок {part}")
            if any(n not in columns or columns[n]["type"] == "text" for n in names):
                raise MaterialError(f"{mid}: числовые колонки {part} не найдены")
            if len({columns[n]["unit"] for n in names}) != 1:
                raise MaterialError(f"{mid}: сумма колонок разных единиц запрещена")
        num_unit = columns[metric["numerator"][0]]["unit"]
        multiplier = decimal_value(metric.get("multiplier", "1"), mid + "/multiplier")
        if metric["operation"] == "sum" and (metric["unit"] != num_unit or multiplier != 1):
            raise MaterialError(f"{mid}: sum сохраняет единицу и multiplier=1")
        if metric["operation"] == "ratio":
            den_unit = columns[metric["denominator"][0]]["unit"]
            expected_unit = "%" if multiplier == 100 and num_unit == den_unit else (
                "ratio" if multiplier == 1 and num_unit == den_unit else f"{num_unit}/{den_unit}")
            if metric["unit"] != expected_unit or (num_unit != den_unit and multiplier != 1):
                raise MaterialError(f"{mid}: несогласованные единицы отношения/множитель; ожидается {expected_unit}")


def calculate(data, spec, *, max_rows=50000):
    if not isinstance(spec, dict):
        raise MaterialError("Спецификация должна быть JSON object")
    parsed = read_csv_bytes(data, delimiter=spec.get("delimiter", ","), max_rows=max_rows)
    validate_spec(spec, parsed["columns"])
    groups = OrderedDict()
    missing_tokens = set(spec["missing_values"])
    for row in parsed["rows"]:
        typed = {}
        for column, value in row["values"].items():
            rule = spec["columns"][column]
            if value in missing_tokens:
                typed[column] = None
            elif rule["type"] == "text":
                typed[column] = value
            else:
                number = decimal_value(value, f"{row['locator']}/{column}")
                if rule["type"] == "integer" and number != number.to_integral_value():
                    raise MaterialError(f"{row['locator']}/{column}: требуется целое число")
                if "min" in rule and number < decimal_value(rule["min"], column + "/min"):
                    raise MaterialError(f"{row['locator']}/{column}: значение меньше min")
                if "max" in rule and number > decimal_value(rule["max"], column + "/max"):
                    raise MaterialError(f"{row['locator']}/{column}: значение больше max")
                typed[column] = number
        if any(typed[c] is None for c in spec["group_by"]):
            raise MaterialError(f"{row['locator']}: пропущена группа/период")
        # Optional pairwise domain constraint (e.g. retained cannot exceed eligible).
        for constraint in spec.get("constraints", []):
            if constraint.get("operation") != "lte" or constraint.get("left") not in typed or constraint.get("right") not in typed:
                raise MaterialError("Поддерживается constraint operation=lte с известными left/right")
            left, right = constraint["left"], constraint["right"]
            if spec["columns"][left]["unit"] != spec["columns"][right]["unit"]:
                raise MaterialError("Constraint сравнивает разные единицы")
            if typed[left] is not None and typed[right] is not None and typed[left] > typed[right]:
                raise MaterialError(f"{row['locator']}: {left} превышает {right}")
        key = tuple(str(typed[c]) for c in spec["group_by"])
        groups.setdefault(key, []).append((row, typed))
    output_groups = []
    for key, members in groups.items():
        metrics = {}
        for metric in spec["metrics"]:
            parts, missing = {}, []
            for part in (["numerator", "denominator"] if metric["operation"] == "ratio" else ["numerator"]):
                names = metric[part]
                absent = [{"locator": row["locator"], "column": name}
                          for row, values in members for name in names if values[name] is None]
                parts[part] = None if absent else exact_sum(values[name] for _, values in members for name in names)
                missing.extend(absent)
            status = "missing" if missing else "ok"
            if status == "ok" and metric["operation"] == "ratio" and parts["denominator"] == 0:
                status = "zero_denominator"
            value = None
            if status == "ok":
                value = rounded_value(parts["numerator"],
                                      parts["denominator"] if metric["operation"] == "ratio" else Decimal(1),
                                      decimal_value(metric.get("multiplier", "1"), "multiplier"),
                                      metric["rounding"])
            metrics[metric["id"]] = {"value": value, "unit": metric["unit"], "status": status,
                                      **{p: None if v is None else str(v) for p, v in parts.items()},
                                      "missing": missing, "definition": metric}
        output_groups.append({"group": dict(zip(spec["group_by"], key)),
                              "locators": [row["locator"] for row, _ in members], "metrics": metrics})
    return {"groups": output_groups, "synthetic": spec["synthetic"],
            "period_column": spec["period_column"], "columns": spec["columns"],
            "missing_policy": "Любой пропуск компонента делает соответствующий агрегат null; строки не отбрасываются",
            "zero_denominator_policy": "null, status=zero_denominator",
            "rounding_method": "Точные десятичные суммы и рациональное ROUND_HALF_UP; округление только результата",
            "numeric_guard": {"max_coefficient_digits": MAX_NUMERIC_DIGITS, "max_abs_exponent": MAX_NUMERIC_EXPONENT}}


def normalize_xlsx(extracted, spec, *, max_rows=50000):
    """Select literal cells by original address; CSV exists only in memory.

    Units are declarations from the import selection, not inferred from formatting.
    Formulas, even with caches, require an explicit business recomputation.
    """
    mapping = spec.get("xlsx")
    if not isinstance(mapping, dict):
        raise MaterialError("XLSX: нужен spec.xlsx с sheet, rows, columns, include_hidden")
    rows, columns = mapping.get("rows"), mapping.get("columns")
    if (not isinstance(rows, list) or not rows or len(rows) > max_rows
            or any(type(r) is not int or not 1 <= r <= 1048576 for r in rows)
            or len(rows) != len(set(rows))):
        raise MaterialError("XLSX: rows — уникальные номера исходных строк в пределах max_rows")
    if (not isinstance(columns, dict) or not isinstance(spec.get("columns"), dict)
            or set(columns) != set(spec["columns"])
            or any(not isinstance(c, str) or not re.fullmatch(r"[A-Z]{1,3}", c) for c in columns.values())
            or len(set(columns.values())) != len(columns)):
        raise MaterialError("XLSX: columns однозначно сопоставляет поля исходным буквам колонок")
    if type(mapping.get("include_hidden")) is not bool:
        raise MaterialError("XLSX: include_hidden должен быть явно true/false")
    sheets = [s for s in extracted.get("sheets", []) if s.get("name") == mapping.get("sheet")]
    if len(sheets) != 1:
        raise MaterialError("XLSX: исходный лист не найден в извлечении")
    sheet = sheets[0]
    if sheet.get("state") != "visible" and not mapping["include_hidden"]:
        raise MaterialError("XLSX: скрытый лист требует явного include_hidden=true")
    cells = {c["address"]: c for c in sheet["cells"]}
    if len(cells) != len(sheet["cells"]):
        raise MaterialError("XLSX: неоднозначные повторяющиеся адреса")
    from openpyxl.utils.cell import range_boundaries, column_index_from_string
    selected = []
    for selection in sheet["selected_ranges"]:
        selected.append((range_boundaries(selection["range"]), selection))
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=spec.get("delimiter", ","), lineterminator="\n")
    writer.writerow(columns)
    provenance = []
    if "" not in spec.get("missing_values", []):
        raise MaterialError("XLSX: missing_values должен включать пустую строку для null-ячеек")
    for row_number in rows:
        values, row_cells = [], {}
        for name, letter in columns.items():
            address = f"{letter}{row_number}"
            cell = cells.get(address)
            if cell is None:
                raise MaterialError(f"XLSX: {address} не входит в извлечённые диапазоны")
            col_number = column_index_from_string(letter)
            declarations = [s for (c1, r1, c2, r2), s in selected
                            if c1 <= col_number <= c2 and r1 <= row_number <= r2]
            if len(declarations) != 1:
                raise MaterialError(f"XLSX: {address} имеет неоднозначное покрытие диапазонами")
            declaration = declarations[0]
            rule = spec["columns"][name]
            if rule.get("type") != "text" and declaration.get("units", {}).get(letter) != rule.get("unit"):
                raise MaterialError(f"XLSX: {address} единица selection не совпадает со spec")
            if cell.get("formula") is not None or cell.get("type") in {"f", "e", "merged"} or cell.get("merged_anchor"):
                raise MaterialError(f"XLSX: {address} формула/ошибка/объединение; используйте проверенные исходные ячейки")
            if (cell.get("hidden_row") or cell.get("hidden_column")) and not mapping["include_hidden"]:
                raise MaterialError(f"XLSX: {address} скрыта; требуется явное include_hidden=true")
            value = cell.get("value")
            if value is not None and rule.get("type") != "text" and cell.get("type") != "n":
                raise MaterialError(f"XLSX: {address} не числовой literal; даты/boolean/текст не преобразуются в число")
            if name == spec.get("period_column") and value != declaration.get("period"):
                raise MaterialError(f"XLSX: {address} период ячейки не совпадает с selection.period")
            values.append("" if value is None else str(value))
            row_cells[name] = {"locator": cell["locator"], "address": address,
                               "value": value, "type": cell["type"],
                               "unit": rule.get("unit"), "period": declaration.get("period"),
                               "number_format": cell.get("number_format")}
        period_name = spec.get("period_column")
        if period_name not in row_cells:
            raise MaterialError("XLSX: period_column отсутствует в сопоставлении")
        row_period = row_cells[period_name]["value"]
        if any(c["period"] != row_period for c in row_cells.values()):
            raise MaterialError(f"XLSX: строка {row_number} объединяет разные или неизвестные периоды диапазонов")
        writer.writerow(values)
        provenance.append({"sheet": sheet["name"], "row": row_number, "cells": row_cells})
    raw = buffer.getvalue().encode("utf-8")
    parsed = read_csv_bytes(raw, delimiter=spec.get("delimiter", ","), max_rows=max_rows)
    locator_map = {}
    for csv_row, origin in zip(parsed["rows"], provenance):
        origin["normalized_locator"] = csv_row["locator"]
        origin["locator"] = "; ".join(c["locator"] for c in origin["cells"].values())
        locator_map[csv_row["locator"]] = origin
    return raw, provenance, locator_map


def run(project, input_path, spec_path, output, *, source_id=None, source_version=None,
        max_bytes=DEFAULT_MAX_BYTES, max_rows=50000):
    input_file, spec_file = scoped(project, input_path), scoped(project, spec_path)
    target = scoped(project, output, must_exist=False)
    if input_file.stat().st_size > max_bytes or spec_file.stat().st_size > max_bytes:
        raise MaterialError("Вход превышает технический предел размера")
    if target.exists():
        raise MaterialError("Результат уже существует; используйте новый версионный путь")
    raw, spec_bytes = input_file.read_bytes(), spec_file.read_bytes()
    spec = json.loads(spec_bytes.decode("utf-8-sig"))
    if not isinstance(spec, dict) or not isinstance(spec.get("synthetic"), bool):
        raise MaterialError("Спецификация должна быть объектом с boolean synthetic")
    if (source_id is None) != (source_version is None):
        raise MaterialError("source-id и source-version задаются вместе")
    source, extraction, normalized, locator_map = None, None, None, None
    calculation_raw = raw
    if source_id is not None:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", source_id) or source_version < 1:
            raise MaterialError("Недопустимая версия/ID источника")
        source_path = scoped(project, f"evidence/sources/{source_id}/v{source_version}/source.json")
        source = json.loads(source_path.read_text(encoding="utf-8"))
        if source.get("id") != source_id or source.get("version") != source_version or source.get("input_sha256") != sha256(raw):
            raise MaterialError("Расчётный вход не совпадает с зарегистрированной версией источника")
        if source.get("kind") not in {"csv", "xlsx"}:
            raise MaterialError("Расчёт требует зарегистрированный CSV или XLSX источник")
        if source["kind"] == "csv" and "xlsx" in spec:
            raise MaterialError("spec.xlsx не относится к зарегистрированному CSV")
        if source["kind"] == "xlsx":
            extract_path = scoped(project, source["extract"]["path"])
            if extract_path.stat().st_size > max_bytes:
                raise MaterialError("XLSX extract превышает технический предел размера")
            extract_raw = extract_path.read_bytes()
            if sha256(extract_raw) != source["extract"]["sha256"]:
                raise MaterialError("Повреждена зарегистрированная версия XLSX extract")
            extraction = json.loads(extract_raw.decode("utf-8"))
            if extraction.get("source_id") != source_id or extraction.get("source_version") != source_version:
                raise MaterialError("XLSX extract не относится к выбранной версии источника")
            calculation_raw, normalized, locator_map = normalize_xlsx(extraction, spec, max_rows=max_rows)
        spec["synthetic"] = bool(spec.get("synthetic") or source.get("synthetic"))
    elif "xlsx" in spec:
        raise MaterialError("XLSX требует зарегистрированные source-id и source-version")
    result = calculate(calculation_raw, spec, max_rows=max_rows)
    if locator_map is not None:
        for group in result["groups"]:
            group["locators"] = [locator_map[loc]["locator"] for loc in group["locators"]]
            for metric in group["metrics"].values():
                for absent in metric["missing"]:
                    absent["locator"] = locator_map[absent["locator"]]["cells"][absent["column"]]["locator"]
        result["normalization"] = {"method": "literal-xlsx-cells-to-in-memory-csv-v1",
                                   "formula_policy": "reject_even_with_cache",
                                   "include_hidden": spec["xlsx"]["include_hidden"], "rows": normalized}
    if source is not None:
        result["provenance"] = {"source_type": source["kind"], "input_sha256": source["input_sha256"],
                                "extraction_method": source["extraction_method"],
                                "limitations": source["limitations"], "extract": source["extract"]}
    result.update({"calculated_at": utc_now(), "tool": "analyze_table", "tool_version": VERSION,
                   "input": {"path": relative(project, input_file), "sha256": sha256(raw)},
                   "spec": {"path": relative(project, spec_file), "sha256": sha256(spec_bytes)},
                   "source": None if source_id is None else {"id": source_id, "version": source_version},
                   "reproduce": {"input": relative(project, input_file), "spec": relative(project, spec_file)}})
    encoded = json_bytes(result)
    write_new(target, encoded)
    return {"artifact": {"path": relative(project, target), "sha256": sha256(encoded)}, "result": result}


def main():
    parser = argparse.ArgumentParser(description="Явные CSV/XLSX суммы и отношения по определённым группам и периодам")
    parser.add_argument("--project", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--spec", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--source-id")
    parser.add_argument("--source-version", type=int)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument("--max-rows", type=int, default=50000)
    args = vars(parser.parse_args())
    args["input_path"], args["spec_path"] = args.pop("input"), args.pop("spec")
    try:
        print(json.dumps(run(**args), ensure_ascii=False, indent=2))
        return 0
    except (MaterialError, OSError, ValueError, InvalidOperation, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
