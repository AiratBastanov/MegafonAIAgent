import copy
import io
import json
import tempfile
import unittest
import zipfile
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET
from unittest.mock import patch

from openpyxl import Workbook
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from scripts import extract_formats as fmt
from scripts import import_materials as imp


def workbook_bytes():
    book = Workbook()
    sheet = book.active
    sheet.title = "Бюджет O'Neil"
    sheet.append(["period", "segment", "cost", "conversion", "date", "cached", "missing", "error", "empty"])
    sheet.append(["2026-11", "agency", 1200.50, 0.25, datetime(2026, 11, 1), "=C2*2", "=C2/0", "=C2/0", None])
    sheet["C2"].number_format = '#,##0.00 "RUB"'
    sheet["D2"].number_format = "0.0%"
    sheet["E2"].number_format = "yyyy-mm-dd"
    sheet.merge_cells("A4:B4")
    sheet["A4"] = "Merged heading"
    sheet.row_dimensions[2].hidden = True
    sheet.column_dimensions.group("D", "E", hidden=True)
    book.create_sheet("Справка").sheet_state = "hidden"
    stream = io.BytesIO()
    book.save(stream)
    # Excel-style caches are deliberately inserted as test data, without
    # pretending that openpyxl calculated them.
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(stream.getvalue())) as incoming, zipfile.ZipFile(output, "w") as outgoing:
        for item in incoming.infolist():
            data = incoming.read(item)
            if item.filename == "xl/worksheets/sheet1.xml":
                root = ET.fromstring(data)
                ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
                for cell in root.findall(".//m:c", ns):
                    if cell.attrib["r"] == "F2":
                        cell.find("m:v", ns).text = "2401"
                    if cell.attrib["r"] == "H2":
                        cell.set("t", "e")
                        cell.find("m:v", ns).text = "#DIV/0!"
                data = ET.tostring(root)
            outgoing.writestr(item, data)
    return output.getvalue()


def selection():
    return {"ranges": [{"sheet": "Бюджет O'Neil", "range": "A1:I4",
                        "units": {"C": "RUB", "D": "ratio"}, "period": "2026-11"}]}


def pdf_bytes(pages=(("Offer costs 1200 RUB per account per month.",), ("No audit log is available.",)), *, encrypted=False, rotated=False, columns=False):
    writer = PdfWriter()
    for texts in pages:
        page = writer.add_blank_page(width=595, height=842)
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
                                 NameObject("/BaseFont"): NameObject("/Helvetica")})
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
        commands = []
        for index, text in enumerate(texts):
            escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            x, y = (320 if columns and index else 50), (750 if columns else 750 - index * 30)
            commands.append(f"BT /F1 12 Tf 1 0 0 1 {x} {y} Tm ({escaped}) Tj ET")
        stream = DecodedStreamObject()
        stream.set_data("\n".join(commands).encode("ascii"))
        page[NameObject("/Contents")] = stream
        if rotated:
            page.rotate(90)
    if pages:
        writer.set_page_label(0, 0, style="/r", start=1)
    if len(pages) > 1:
        writer.set_page_label(1, len(pages) - 1, style="/D", start=1)
    if encrypted:
        writer.encrypt("synthetic-fixture-only")
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


class XlsxTests(unittest.TestCase):
    def test_cell_limit_precedes_merged_cell_allocation_and_handles_utf16(self):
        selected = {"ranges": [{"sheet": "Sheet", "range": "A1", "units": {}, "period": None}]}
        merged_book = Workbook()
        merged_book.active["A1"] = "anchor"
        merged_book.active.merge_cells("A1:J10")
        merged_raw = io.BytesIO()
        merged_book.save(merged_raw)

        book = Workbook()
        for number in range(1, 21):
            book.active.cell(number, 1, number)
        raw = io.BytesIO()
        book.save(raw)
        utf16 = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(raw.getvalue())) as incoming, zipfile.ZipFile(utf16, "w") as outgoing:
            for entry in incoming.infolist():
                data = incoming.read(entry)
                if entry.filename == "xl/worksheets/sheet1.xml":
                    data = ET.tostring(ET.fromstring(data), encoding="utf-16", xml_declaration=True)
                outgoing.writestr(entry, data)
        for candidate in (merged_raw.getvalue(), utf16.getvalue()):
            with self.subTest(bytes=len(candidate)), patch("openpyxl.load_workbook") as load:
                with self.assertRaisesRegex(fmt.FormatError, "предел ячеек книги"):
                    fmt.extract_xlsx(candidate, selected, max_cells=5)
                load.assert_not_called()

    def test_coordinate_types_formats_missing_and_structures(self):
        result = fmt.extract_xlsx(workbook_bytes(), selection())
        sheet = result["sheets"][0]
        cells = {cell["address"]: cell for cell in sheet["cells"]}
        self.assertEqual(sheet["name"], "Бюджет O'Neil")
        self.assertEqual(cells["C2"]["locator"], "'Бюджет O''Neil'!C2")
        self.assertEqual(cells["C2"]["value"], 1200.5)
        self.assertEqual(cells["D2"]["value"], 0.25)
        self.assertEqual(cells["D2"]["number_format"], "0.0%")
        self.assertEqual(cells["E2"]["value"], "2026-11-01T00:00:00")
        self.assertEqual(cells["E2"]["type"], "d")
        self.assertEqual(cells["I2"]["type"], "blank")
        self.assertIsNone(cells["I2"]["value"])
        self.assertTrue(cells["C2"]["hidden_row"])
        self.assertTrue(cells["E2"]["hidden_column"])
        self.assertEqual(cells["B4"]["merged_anchor"], "A4")
        self.assertIsNone(cells["B4"]["value"])
        self.assertEqual(cells["B4"]["type"], "merged")
        self.assertEqual(cells["A4"]["merged_anchor"], "A4")
        self.assertEqual(result["workbook_sheets"][1], {"name": "Справка", "state": "hidden"})
        self.assertEqual(sheet["selected_ranges"][0]["units"]["C"], "RUB")
        self.assertEqual(sheet["selected_ranges"][0]["period"], "2026-11")

    def test_formula_is_separate_from_untrusted_present_missing_error_cache(self):
        cells = {cell["address"]: cell for cell in fmt.extract_xlsx(workbook_bytes(), selection())["sheets"][0]["cells"]}
        for address in ("F2", "G2", "H2"):
            self.assertEqual(cells[address]["type"], "f")
            self.assertIsNone(cells[address]["value"])
            self.assertTrue(cells[address]["formula"].startswith("="))
            self.assertEqual(cells[address]["cache_freshness"], "unknown")
        self.assertEqual(cells["F2"]["cached_value"], 2401)
        self.assertEqual(cells["F2"]["cache_status"], "present")
        self.assertEqual(cells["G2"]["cache_status"], "missing")
        self.assertIsNone(cells["G2"]["cached_value"])
        self.assertEqual(cells["H2"]["cache_status"], "error")
        self.assertEqual(cells["H2"]["cached_value"], "#DIV/0!")

    def test_selection_overlap_unknown_units_and_bounds(self):
        bad = selection()
        bad["ranges"].append(copy.deepcopy(bad["ranges"][0]))
        with self.assertRaisesRegex(fmt.FormatError, "пересекаются"):
            fmt.extract_xlsx(workbook_bytes(), bad)
        bad = selection()
        bad["ranges"][0]["period"] = None
        bad["ranges"][0]["units"] = {"C": None}
        result = fmt.extract_xlsx(workbook_bytes(), bad)
        self.assertIsNone(result["selection"]["ranges"][0]["units"]["C"])
        bad["ranges"][0]["range"] = "A1:XFD1048576"
        with self.assertRaisesRegex(fmt.FormatError, "предел ячеек"):
            fmt.extract_xlsx(workbook_bytes(), bad)
        with self.assertRaisesRegex(fmt.FormatError, "распаковки"):
            fmt.extract_xlsx(workbook_bytes(), selection(), max_unpacked=100)

    def test_external_links_macro_and_xml_entities_are_actionable(self):
        for filename, payload, expected in (("xl/externalLinks/externalLink1.xml", b"<x/>", "Внешние связи"),
                                             ("xl/vbaProject.bin", b"artificial-marker", "макросами"),
                                             ("custom.xml", '<!DOCTYPE x [<!ENTITY a "marker">]><x>&a;</x>'.encode("utf-16"), "DTD/entities")):
            stream = io.BytesIO(workbook_bytes())
            with zipfile.ZipFile(stream, "a") as archive:
                archive.writestr(filename, payload)
            with self.subTest(filename=filename), self.assertRaisesRegex(fmt.FormatError, expected):
                fmt.extract_xlsx(stream.getvalue(), selection())


class PdfTests(unittest.TestCase):
    def test_physical_pages_labels_and_exact_fragments(self):
        result = fmt.extract_pdf(pdf_bytes())
        self.assertEqual(result["page_count"], 2)
        self.assertEqual([page["physical_page"] for page in result["pages"]], [1, 2])
        self.assertEqual([page["page_label"] for page in result["pages"]], ["i", "1"])
        first, second = result["pages"]
        self.assertEqual(first["blocks"][0]["text"], "Offer costs 1200 RUB per account per month.")
        self.assertEqual(second["blocks"][0]["text"], "No audit log is available.")
        self.assertEqual(second["blocks"][0]["locator"], "physical-page:2/block:1")
        self.assertFalse(result["visual_layout_verified"])
        self.assertEqual(result["evidence_status"], "extracted_not_claim_verified")

    def test_no_text_and_encrypted_and_corrupt_fail_without_empty_success(self):
        for raw, expected in ((pdf_bytes(pages=((),)), "нет пригодного текстового слоя"),
                              (pdf_bytes(encrypted=True), "Зашифрованный PDF"),
                              (b"not a PDF", "Не удалось извлечь PDF"),
                              (pdf_bytes(pages=(("Text",), ())), "physical page 2")):
            with self.subTest(expected=expected), self.assertRaisesRegex(fmt.FormatError, expected):
                fmt.extract_pdf(raw)

    def test_detect_material_layout_ambiguity_and_rotation(self):
        page = fmt.extract_pdf(pdf_bytes(pages=(("Customer group", "Costs 9000 RUB"),), columns=True))["pages"][0]
        self.assertEqual(page["status"], "needs_layout_review")
        self.assertTrue(page["layout_warnings"])
        with self.assertRaisesRegex(fmt.FormatError, "повёрнутая"):
            fmt.extract_pdf(pdf_bytes(rotated=True))

    def test_configured_pdf_limits(self):
        for limits in ({"max_pages": 1}, {"max_page_stream": 10}, {"max_text_chars": 10}):
            with self.subTest(limits=limits), self.assertRaises(fmt.FormatError):
                fmt.extract_pdf(pdf_bytes(), **limits)


class FormatRegistrationTests(unittest.TestCase):
    def test_version_provenance_reuse_original_and_correction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "inputs").mkdir()
            original = workbook_bytes()
            (root / "inputs/costs.xlsx").write_bytes(original)
            (root / "inputs/selection.json").write_bytes(imp.json_bytes(selection()))
            first = imp.register(root, "S001", "inputs/costs.xlsx", "xlsx", synthetic=True, selection_path="inputs/selection.json")
            second = imp.register(root, "S001", "inputs/costs.xlsx", "xlsx", synthetic=True, selection_path="inputs/selection.json")
            self.assertTrue(second["reused"])
            self.assertEqual((root / first["source"]["original"]["path"]).read_bytes(), original)
            extracted = json.loads((root / first["source"]["extract"]["path"]).read_text(encoding="utf-8"))
            self.assertEqual(extracted["source_version"], 1)
            self.assertTrue(extracted["synthetic"])
            self.assertEqual(first["source"]["kind"], "xlsx")
            revised = selection()
            revised["ranges"][0]["units"]["C"] = "RUB/month"
            (root / "inputs/selection-v2.json").write_bytes(imp.json_bytes(revised))
            third = imp.register(root, "S001", "inputs/costs.xlsx", "xlsx", synthetic=True, selection_path="inputs/selection-v2.json")
            self.assertEqual(third["source"]["version"], 2)
            self.assertEqual((root / first["source"]["original"]["path"]).read_bytes(), original)
            raw_pdf = pdf_bytes()
            (root / "inputs/brief.pdf").write_bytes(raw_pdf)
            pdf = imp.register(root, "S002", "inputs/brief.pdf", "pdf", synthetic=True)
            self.assertEqual(pdf["source"]["input_sha256"], imp.sha256(raw_pdf))
            self.assertIn("pypdf/7.1.0", pdf["source"]["extraction_method"])

    def test_failed_import_does_not_publish_source_record(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scan.pdf").write_bytes(pdf_bytes(pages=((),)))
            with self.assertRaises(imp.MaterialError):
                imp.register(root, "S001", "scan.pdf", "pdf")
            self.assertFalse((root / "evidence/sources/S001").exists())


if __name__ == "__main__":
    unittest.main()
