"""Project-local arithmetic and source checks. No model, network or source execution."""
import argparse
import hashlib
import json
import posixpath
from decimal import Decimal as D, ROUND_CEILING, ROUND_HALF_UP
from fractions import Fraction as F
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def fmt(value):
    return str(value.quantize(D("0.01"), rounding=ROUND_HALF_UP))


def rational_fmt(value):
    sign = "-" if value < 0 else ""
    value = abs(value)
    cents = (value.numerator * 200 + value.denominator) // (2 * value.denominator)
    return f"{sign}{cents // 100}.{cents % 100:02d}"


def calculate():
    spec_path = "inputs/analysis-calculation-spec-v2.json"
    spec = read(spec_path)
    funnel = read(spec["inputs"]["funnel"])
    econ = read(spec["inputs"]["economics"])
    sensitivity = read(spec["inputs"]["sensitivity"])
    meta = read("evidence/sources/S002/v1/source.json")
    original = meta["original"]["path"]
    assert digest(original) == meta["input_sha256"]
    assert digest(meta["extract"]["path"]) == meta["extract"]["sha256"]
    for calculation in (funnel, econ):
        assert calculation["input"]["sha256"] == digest(original)
        assert calculation["spec"]["sha256"] == digest(calculation["spec"]["path"])
        assert calculation["source"] == {"id": "S002", "version": 1}

    # Independent path: ZIP/XML literal cells, without openpyxl or imported normalization.
    raw = {}
    sheet_meta = []
    with ZipFile(ROOT / original) as z:
        workbook = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        targets = {r.attrib["Id"]: r.attrib["Target"] for r in rels}
        for sheet in workbook.find("s:sheets", NS):
            name = sheet.attrib["name"]
            sheet_meta.append({"name": name, "state": sheet.attrib.get("state", "visible")})
            if name not in ("Воронка", "Экономика"):
                continue
            rid = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            target = targets[rid]
            path = target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)
            xml = ET.fromstring(z.read(path))
            cells = {}
            for c in xml.findall(".//s:sheetData/s:row/s:c", NS):
                if c.attrib.get("t") == "inlineStr":
                    value = "".join(t.text or "" for t in c.findall("s:is//s:t", NS))
                else:
                    value = c.findtext("s:v", default=None, namespaces=NS)
                cells[c.attrib["r"]] = {"value": value, "formula": c.findtext("s:f", default=None, namespaces=NS)}
            raw[name] = cells

    checked_cells = 0
    for calculation in (funnel, econ):
        for row in calculation["normalization"]["rows"]:
            for field in row["cells"].values():
                cell = raw[row["sheet"]].get(field["address"], {"value": None, "formula": None})
                assert cell["formula"] is None
                if field["value"] is None:
                    assert cell["value"] is None
                elif field["type"] == "n":
                    assert F(cell["value"]) == F(str(field["value"]))
                else:
                    assert cell["value"] == field["value"]
                checked_cells += 1

    historical = []
    for row, group in zip(funnel["normalization"]["rows"], funnel["groups"]):
        cells = row["cells"]
        values = {key: D(str(cells[key]["value"])) for key in ("contacted", "trials", "interest", "paid30", "revenue30", "variable30")}
        rational = {key: F(raw[row["sheet"]][cells[key]["address"]]["value"]) for key in values}
        expected = {
            "paid_per_trial_pct": 100 * rational["paid30"] / rational["trials"],
            "interest_per_trial_pct": 100 * rational["interest"] / rational["trials"],
            "paid_per_contact_pct": 100 * rational["paid30"] / rational["contacted"],
            "revenue30": rational["revenue30"], "variable30": rational["variable30"]
        }
        for key, value in expected.items():
            assert group["metrics"][key]["value"] == rational_fmt(value)
        assert group["metrics"]["acquisition"]["value"] is None
        assert group["metrics"]["acquisition"]["status"] == "missing"
        contribution = values["revenue30"] - values["variable30"]
        assert F(contribution) == rational["revenue30"] - rational["variable30"]
        historical.append({"segment": group["group"]["segment"], "row": row["row"],
                           "contribution_rub": fmt(contribution), "acquisition_rub": None,
                           "source_locators": [cells[key]["locator"] for key in ("revenue30", "variable30", "acquisition")]})

    pooled_paid = sum(D(str(r["cells"]["paid30"]["value"])) for r in funnel["normalization"]["rows"])
    pooled_trials = sum(D(str(r["cells"]["trials"]["value"])) for r in funnel["normalization"]["rows"])
    pooled_pct = fmt(100 * pooled_paid / pooled_trials)
    independent_paid = sum(F(raw["Воронка"][f"F{r}"]["value"]) for r in (3, 4))
    independent_trials = sum(F(raw["Воронка"][f"D{r}"]["value"]) for r in (3, 4))
    assert pooled_pct == rational_fmt(100 * independent_paid / independent_trials)

    base = {key: D(value["value"]) for key, value in econ["groups"][0]["metrics"].items()}
    econ_cells = econ["normalization"]["rows"][0]["cells"]
    independent = {key: F(raw["Экономика"][econ_cells[key]["address"]]["value"]) for key in base}
    for key, value in base.items():
        assert F(value) == independent[key]
    scenarios = []
    for minutes_text in sensitivity["support_minutes_scenarios"]:
        minutes = D(minutes_text)
        support = minutes * base["hourly_cost"] / 60
        unit = base["price"] - base["infra"] - support
        coverage = int((base["fixed"] / unit).to_integral_value(rounding=ROUND_CEILING)) if unit > 0 else None
        # Different expression and exact rational arithmetic on original XML cells.
        unit_check = (60 * (independent["price"] - independent["infra"]) - F(minutes_text) * independent["hourly_cost"]) / 60
        assert F(unit) == unit_check
        if coverage is not None:
            assert (coverage - 1) * unit_check < independent["fixed"] <= coverage * unit_check
        balances = []
        for accounts_text in sensitivity["accounts_scenarios"]:
            accounts = D(accounts_text)
            balance = accounts * unit - base["fixed"]
            balance_check = F(accounts_text) * independent["price"] - (F(accounts_text) * independent["infra"] + F(accounts_text) * F(minutes_text) * independent["hourly_cost"] / 60 + independent["fixed"])
            assert F(balance) == balance_check
            payback = fmt(base["setup"] / balance) if balance > 0 else None
            if payback is not None:
                assert payback == rational_fmt(independent["setup"] / balance_check)
            balances.append({"accounts": accounts_text, "monthly_balance_rub": fmt(balance), "conditional_setup_payback_months": payback})
        scenarios.append({"support_minutes": minutes_text, "support_cost_rub": fmt(support),
                          "unit_contribution_rub": fmt(unit), "fixed_coverage_accounts": coverage, "balances": balances})

    extract = read("evidence/sources/S002/v1/extract.json")
    formulas = []
    for sheet in extract["sheets"][:2]:
        for cell in sheet["cells"]:
            if cell["formula"]:
                assert cell["cache_status"] == "missing"
                original_cell = raw[sheet["name"]][cell["address"]]
                assert "=" + original_cell["formula"] == cell["formula"]
                assert original_cell["value"] in (None, "")
                formulas.append({"locator": cell["locator"], "cache_status": "missing", "used": False})

    # Compare original PDF literal Tj operators with extract and fixture manifest.
    pdf_meta = read("evidence/sources/S001/v1/source.json")
    assert digest(pdf_meta["original"]["path"]) == pdf_meta["input_sha256"]
    pdf = PdfReader(ROOT / pdf_meta["original"]["path"])
    pdf_extract = read(pdf_meta["extract"]["path"])
    manifest = read("inputs/pdf-text-manifest-v1.json")
    assert len(pdf.pages) == len(pdf_extract["pages"]) == len(manifest["physical_pages"])
    pages = []
    for page, extracted, expected in zip(pdf.pages, pdf_extract["pages"], manifest["physical_pages"]):
        assert not extracted["layout_warnings"]
        operations = page.get_contents().operations
        assert not any(op in (b"TJ", b"'", b'"') for _, op in operations)
        lines = [str(args[0]) for args, op in operations if op == b"Tj"]
        assert lines == expected["lines"] == [b["text"] for b in extracted["blocks"]]
        assert lines[-1] == f"Printed label: {expected['label']} (physical page {expected['page']})."
        pages.append({"physical_page": expected["page"], "printed_label": expected["label"], "matched_lines": len(lines)})

    referenced_paths = [spec_path, *spec["inputs"].values(), original, meta["extract"]["path"],
                        pdf_meta["original"]["path"], pdf_meta["extract"]["path"],
                        "inputs/pdf-text-manifest-v1.json", "evidence/reproduce-analysis-v2.py"]
    return {
        "record_type": "project_analysis_calculation", "synthetic": True,
        "source": {"id": "S002", "version": 1},
        "inputs": [{"path": p, "sha256": digest(p)} for p in referenced_paths],
        "definitions": spec["definitions"], "historical": historical,
        "pooled_paid_per_trial": {"numerator": str(pooled_paid), "denominator": str(pooled_trials), "pct": pooled_pct},
        "economics_scenarios": scenarios,
        "checks": {"status": "passed", "normalized_cells_matched_to_original_xml": checked_cells,
                   "arithmetic": "Decimal primary, Fraction from original XLSX XML independently; all metric values, missing acquisition, coverage bounds and scenario balances checked",
                   "workbook_sheets": sheet_meta, "excluded_formulas": formulas, "pdf_pages": pages,
                   "pdf_method": "Original Tj strings compared with registered blocks and fixture manifest; no visual rendering or independent business validation"},
        "limitations": sensitivity["limitations"],
        "reproduce": ".\\.venv\\Scripts\\python.exe -X utf8 projects/task06-rehearsal/evidence/reproduce-analysis-v2.py --check"
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Read-only comparison with saved result")
    args = parser.parse_args()
    result = calculate()
    output = ROOT / "evidence/calculations/analysis-derived-v1.json"
    if args.check:
        assert result == json.loads(output.read_text(encoding="utf-8"))
    else:
        with output.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    print(json.dumps({"ok": True, "mode": "check" if args.check else "write", "checks": result["checks"],
                      "historical": result["historical"], "economics_scenarios": result["economics_scenarios"]}, ensure_ascii=False))
