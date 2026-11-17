"""Explicit decimal CSV aggregation; no inferred columns, missing-value coercion or eval."""
from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

try:
    from .import_materials import (MaterialError, DEFAULT_MAX_BYTES, json_bytes, read_csv_bytes,
                                   relative, scoped, sha256, utc_now, write_new)
except ImportError:
    from import_materials import (MaterialError, DEFAULT_MAX_BYTES, json_bytes, read_csv_bytes,
                                  relative, scoped, sha256, utc_now, write_new)

VERSION = "1.0"


def decimal_value(value, name):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise MaterialError(f"Некорректное число: {name}") from exc
    if not result.is_finite():
        raise MaterialError(f"Не конечное число: {name}")
    return result


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
                parts[part] = None if absent else sum((values[name] for _, values in members for name in names), Decimal(0))
                missing.extend(absent)
            status = "missing" if missing else "ok"
            if status == "ok" and metric["operation"] == "ratio" and parts["denominator"] == 0:
                status = "zero_denominator"
            value = None
            if status == "ok":
                value = parts["numerator"]
                if metric["operation"] == "ratio":
                    value = value / parts["denominator"]
                value *= decimal_value(metric.get("multiplier", "1"), "multiplier")
                value = str(value.quantize(Decimal(1).scaleb(-metric["rounding"]), rounding=ROUND_HALF_UP))
            metrics[metric["id"]] = {"value": value, "unit": metric["unit"], "status": status,
                                      **{p: None if v is None else str(v) for p, v in parts.items()},
                                      "missing": missing, "definition": metric}
        output_groups.append({"group": dict(zip(spec["group_by"], key)),
                              "locators": [row["locator"] for row, _ in members], "metrics": metrics})
    return {"groups": output_groups, "synthetic": spec["synthetic"],
            "period_column": spec["period_column"], "columns": spec["columns"],
            "missing_policy": "Любой пропуск компонента делает соответствующий агрегат null; строки не отбрасываются",
            "zero_denominator_policy": "null, status=zero_denominator",
            "rounding_method": "Decimal ROUND_HALF_UP; округление только результата"}


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
    if source_id is not None:
        import re
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", source_id) or source_version < 1:
            raise MaterialError("Недопустимая версия/ID источника")
        source_path = scoped(project, f"evidence/sources/{source_id}/v{source_version}/source.json")
        source = json.loads(source_path.read_text(encoding="utf-8"))
        if source.get("id") != source_id or source.get("version") != source_version or source.get("input_sha256") != sha256(raw):
            raise MaterialError("Расчётный вход не совпадает с зарегистрированной версией источника")
        if source.get("kind") != "csv":
            raise MaterialError("Расчёт требует зарегистрированный CSV источник")
        spec["synthetic"] = bool(spec.get("synthetic") or source.get("synthetic"))
    result = calculate(raw, spec, max_rows=max_rows)
    result.update({"calculated_at": utc_now(), "tool": "analyze_table", "tool_version": VERSION,
                   "input": {"path": relative(project, input_file), "sha256": sha256(raw)},
                   "spec": {"path": relative(project, spec_file), "sha256": sha256(spec_bytes)},
                   "source": None if source_id is None else {"id": source_id, "version": source_version},
                   "reproduce": {"input": relative(project, input_file), "spec": relative(project, spec_file)}})
    encoded = json_bytes(result)
    write_new(target, encoded)
    return {"artifact": {"path": relative(project, target), "sha256": sha256(encoded)}, "result": result}


def main():
    parser = argparse.ArgumentParser(description="Явные CSV суммы и отношения по определённым группам и периодам")
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
