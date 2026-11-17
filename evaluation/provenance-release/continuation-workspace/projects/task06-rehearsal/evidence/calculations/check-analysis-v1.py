"""Локальная арифметика и сверка исходных файлов; без выбора стратегии и сети."""
import argparse
import hashlib
import json
import math
import time
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from fractions import Fraction
from pathlib import Path

import openpyxl
import fitz


ROOT = Path(__file__).resolve().parents[2]
D = Decimal
checks = []
started = time.perf_counter()


def path(relative):
    target = (ROOT / relative).resolve()
    if not target.is_relative_to(ROOT):
        raise ValueError("Путь вне выбранного проекта")
    return target


def read(relative):
    return json.loads(path(relative).read_text(encoding="utf-8"))


def ref(relative):
    return {"path": relative, "sha256": hashlib.sha256(path(relative).read_bytes()).hexdigest()}


def check(identifier, condition, detail):
    if not condition:
        raise AssertionError(f"{identifier}: {detail}")
    checks.append({"id": identifier, "status": "passed", "detail": detail})


def amount(value):
    return str(value.quantize(D("0.01"), rounding=ROUND_HALF_UP))


parser = argparse.ArgumentParser()
parser.add_argument("--output", default="evidence/calculations/derived-analysis-v1.json")
parser.add_argument("--verification-output", default="evidence/calculations/verification-v1.json")
args = parser.parse_args()
targets = [path(args.output), path(args.verification_output)]
if targets[0] == targets[1] or any(p.exists() for p in targets):
    raise FileExistsError("Требуются два разных новых пути; старые результаты не перезаписываются")

pdf_meta = read("evidence/sources/S001/v1/source.json")
xlsx_meta = read("evidence/sources/S002/v1/source.json")
for meta in (pdf_meta, xlsx_meta):
    for kind in ("original", "extract"):
        item = meta[kind]
        check(f"hash-{meta['id']}-{kind}", ref(item["path"])["sha256"] == item["sha256"], item["path"])

pdf_extract = read(pdf_meta["extract"]["path"])
manifest = read("inputs/pdf-text-manifest-v1.json")
pdf = fitz.open(path(pdf_meta["original"]["path"]))
check("pdf-page-count", len(pdf) == len(manifest["physical_pages"]) == len(pdf_extract["pages"]), "Число физических страниц оригинала, manifest и extract совпадает")
for expected, extracted, original in zip(manifest["physical_pages"], pdf_extract["pages"], pdf):
    lines = [line.strip() for line in original.get_text("text").splitlines() if line.strip()]
    blocks = [block["text"].strip() for block in extracted["blocks"]]
    check(f"pdf-page-{expected['page']}", lines == expected["lines"] == blocks,
          f"physical_page={expected['page']}: полный текстовый слой совпал; визуальная вёрстка не проверялась")

xlsx_extract = read(xlsx_meta["extract"]["path"])
book = openpyxl.load_workbook(path(xlsx_meta["original"]["path"]), data_only=False, keep_links=False)
cache = openpyxl.load_workbook(path(xlsx_meta["original"]["path"]), data_only=True, keep_links=False)
cell_count = 0
for sheet in xlsx_extract["sheets"][:2]:
    original = book[sheet["name"]]
    check(f"layout-{sheet['name']}", original.sheet_state == sheet["state"] and
          set(map(str, original.merged_cells.ranges)) == {r["range"] for r in sheet["merged_ranges"]},
          "Состояние листа и объединённые диапазоны совпали с сохранённым извлечением")
    for extracted in sheet["cells"]:
        address = extracted["address"]
        if original[address].row == 1:
            continue
        value = original[address].value
        if isinstance(value, datetime):
            value = value.isoformat()
        expected = extracted["formula"] if extracted["type"] == "f" else extracted["value"]
        if value != expected:
            raise AssertionError(f"Несовпадение {sheet['name']}!{address}")
        cell_count += 1
check("xlsx-literals", cell_count == 53, "53 ячейки строк заголовков и данных двух рабочих листов сверены с original.xlsx")
for sheet_name, address in (("Воронка", "K3"), ("Воронка", "K4"), ("Экономика", "J3")):
    check(f"cache-{sheet_name}-{address}", cache[sheet_name][address].value is None,
          "Кэш формулы отсутствует; формула не выполнялась и не использовалась как число")
check("hidden-column", book["Воронка"].column_dimensions["K"].hidden is True, "K скрыта; расчёт использует явные числовые ячейки")

funnel = read("evidence/calculations/funnel-v1.json")
econ = read("evidence/calculations/economics-inputs-v1.json")
for name, calc, spec_path in (("funnel", funnel, "inputs/metrics-funnel-v1.json"),
                              ("economics", econ, "inputs/metrics-economics-v1.json")):
    check(f"calc-origin-{name}", calc["input"]["sha256"] == xlsx_meta["input_sha256"] and
          calc["source"] == {"id": "S002", "version": 1} and calc["synthetic"] is True and
          calc["spec"]["sha256"] == ref(spec_path)["sha256"], "Расчёт закреплён к S002/v1 и исходному spec")

historical = []
for row in (3, 4):
    sheet = book["Воронка"]
    segment = sheet[f"B{row}"].value
    group = next(g for g in funnel["groups"] if g["group"]["segment"] == segment)
    metrics = group["metrics"]
    for metric, numerator, denominator in (("paid_per_trial_pct", "F", "D"),
                                            ("interest_per_trial_pct", "E", "D"),
                                            ("paid_per_contact_pct", "F", "C")):
        exact = Fraction(sheet[f"{numerator}{row}"].value, sheet[f"{denominator}{row}"].value) * 100
        observed = metrics[metric]
        check(f"funnel-{row}-{metric}", observed["status"] == "ok" and Fraction(observed["value"]) == exact,
              f"{numerator}{row}/{denominator}{row}*100; Fraction по оригиналу совпадает с analyze_table")
    for metric, column in (("revenue30", "G"), ("variable30", "H")):
        check(f"funnel-{row}-{metric}", D(metrics[metric]["value"]) == D(sheet[f"{column}{row}"].value), "Сумма совпала с original.xlsx")
    check(f"acquisition-{row}", sheet[f"I{row}"].value is None and metrics["acquisition"]["value"] is None and
          metrics["acquisition"]["status"] == "missing", "Отсутствующие расходы не приняты за ноль")
    contribution = D(metrics["revenue30"]["value"]) - D(metrics["variable30"]["value"])
    check(f"contribution-{row}", contribution == sheet[f"G{row}"].value - sheet[f"H{row}"].value, "Повторная разность по оригиналу")
    historical.append({"segment": segment, "period": sheet[f"A{row}"].value,
                       "locator": f"'Воронка'!G{row}:H{row}", "contribution_after_listed_variable_rub": amount(contribution),
                       "acquisition_rub": None, "profit_rub": None})

parameters = {name: D(metric["value"]) for name, metric in econ["groups"][0]["metrics"].items()}
for name, column in (("price", "C"), ("infra", "D"), ("support_minutes", "E"), ("hourly_cost", "F"),
                      ("fixed", "G"), ("setup", "H"), ("accounts", "I")):
    check(f"parameter-{name}", parameters[name] == D(book["Экономика"][f"{column}3"].value), f"'Экономика'!{column}3")

assumptions = read("inputs/economics-sensitivity-v1.json")
rows = []
for minutes_text in assumptions["support_minutes_scenarios"]:
    minutes = D(minutes_text)
    support = minutes * parameters["hourly_cost"] / 60
    margin = parameters["price"] - parameters["infra"] - support
    threshold = int((parameters["fixed"] / margin).to_integral_value(rounding=ROUND_CEILING)) if margin > 0 else None
    original_econ = book["Экономика"]
    rational_margin = Fraction(original_econ["C3"].value - original_econ["D3"].value) - Fraction(minutes_text) * original_econ["F3"].value / 60
    check(f"margin-{minutes_text}", Fraction(margin) == rational_margin, "Decimal и Fraction дают одинаковый вклад")
    check(f"threshold-{minutes_text}", threshold == math.ceil(Fraction(original_econ["G3"].value) / rational_margin) and
          (threshold - 1) * margin < parameters["fixed"] <= threshold * margin, "Проверена минимальность целого порога покрытия заданных fixed")
    outcomes = []
    for accounts_text in assumptions["accounts_scenarios"]:
        accounts = D(accounts_text)
        surplus = accounts * margin - parameters["fixed"]
        alternative = Fraction(accounts_text) * original_econ["C3"].value - (
            Fraction(accounts_text) * original_econ["D3"].value +
            Fraction(accounts_text) * Fraction(minutes_text) * original_econ["F3"].value / 60 + original_econ["G3"].value)
        check(f"surplus-{minutes_text}-{accounts_text}", Fraction(surplus) == alternative,
              "N*(price-infra-support)-fixed сверено с N*price-(N*infra+N*support+fixed)")
        payback = parameters["setup"] / surplus if surplus > 0 else None
        outcomes.append({"accounts": accounts_text, "monthly_residual_before_unknown_costs_rub": amount(surplus),
                         "setup_payback_months_if_stationary": amount(payback) if payback is not None else None,
                         "setup_payback_status": "conditional" if payback is not None else "no_positive_residual"})
    rows.append({"support_minutes_per_account_month": minutes_text, "support_cost_rub": amount(support),
                 "contribution_rub_per_account_month": amount(margin), "accounts_to_cover_listed_fixed": str(threshold),
                 "outcomes": outcomes})

base_row = next(row for row in rows if D(row["support_minutes_per_account_month"]) == parameters["support_minutes"])
base_outcome = next(row for row in base_row["outcomes"] if D(row["accounts"]) == parameters["accounts"])
stamp = datetime.now(timezone.utc).isoformat()
input_paths = ["evidence/sources/S001/v1/original.pdf", "evidence/sources/S001/v1/extract.json",
               "evidence/sources/S002/v1/original.xlsx", "evidence/sources/S002/v1/extract.json",
               "inputs/pdf-text-manifest-v1.json", "inputs/DATA_DICTIONARY.md", "inputs/metrics-funnel-v1.json",
               "inputs/metrics-economics-v1.json", "inputs/economics-sensitivity-v1.json",
               "evidence/calculations/funnel-v1.json", "evidence/calculations/economics-inputs-v1.json"]
result = {"record_type": "analytical_calculation", "tool": "task06_analysis_v1", "synthetic": True,
          "calculated_at": stamp, "source_versions": [{"id": "S001", "version": 1}, {"id": "S002", "version": 1}],
          "inputs": [ref(p) for p in input_paths], "historical_contribution": historical,
          "formulas": {"support": "support_minutes * hourly_cost / 60",
                       "contribution": "price - infra - support", "listed_fixed_threshold": "ceil(fixed / contribution), contribution > 0",
                       "monthly_residual": "accounts * contribution - fixed",
                       "setup_payback": "setup / monthly_residual only if monthly_residual > 0 and repeated unchanged"},
          "parameters": {k: str(v) for k, v in parameters.items()}, "scenario_period": "2026-11-scenario",
          "base_case": {**base_row, "outcomes": [base_outcome]}, "sensitivity": rows,
          "unknown_costs": {"acquisition": None, "taxes": None, "renewals": None, "exit": None},
          "limitations": assumptions["limitations"],
          "reproduce": {**ref("evidence/calculations/check-analysis-v1.py"),
                        "command": "python projects/task06-rehearsal/evidence/calculations/check-analysis-v1.py --output evidence/calculations/derived-recheck-v1.json --verification-output evidence/calculations/verification-recheck-v1.json"}}
verification = {"record_type": "analytical_verification", "synthetic": True, "checked_at": stamp,
                "result": "passed", "checks": checks, "check_count": len(checks),
                "method": "Оригинальные XLSX literals + Fraction; второй вид выражения; PyMuPDF original text layer + saved manifest + pypdf extract",
                "limits": ["Та же модель-координатор; независимый агент и человек не участвовали",
                           "PDF сверялся другим движком PyMuPDF; manifest и extract имеют то же происхождение и не являются независимыми источниками",
                           "Визуальная вёрстка, реальные платежи, производственный продукт и рынок не проверялись"],
                "libraries": {"openpyxl": openpyxl.__version__, "PyMuPDF": fitz.VersionBind},
                "inputs": result["inputs"], "script": ref("evidence/calculations/check-analysis-v1.py"),
                "measured_script_seconds": str(round(time.perf_counter() - started, 6))}
for target, payload in zip(targets, (result, verification)):
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
book.close()
cache.close()
pdf.close()
print(json.dumps({"ok": True, "check_count": len(checks), "base_case": result["base_case"],
                  "historical_contribution": historical, "sensitivity": rows,
                  "outputs": [str(p.relative_to(ROOT)) for p in targets]}, ensure_ascii=False, indent=2))
