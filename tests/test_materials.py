import copy
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts import analyze_table as calc
from scripts import import_materials as imp


def docx(body):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>' + body + "</w:body></w:document>")
    return buffer.getvalue()


def paragraph(text):
    return "<w:p><w:r><w:t>" + text + "</w:t></w:r></w:p>"


def specification():
    return {"group_by": ["period", "segment"], "period_column": "period",
            "columns": {"period": {"type": "text", "unit": "month"},
                        "segment": {"type": "text", "unit": "category"},
                        "eligible": {"type": "integer", "unit": "users", "min": "0"},
                        "retained": {"type": "integer", "unit": "users", "min": "0"}},
            "metrics": [{"id": "retention", "operation": "ratio", "numerator": ["retained"],
                         "denominator": ["eligible"], "multiplier": "100", "unit": "%", "rounding": 2}],
            "constraints": [{"operation": "lte", "left": "retained", "right": "eligible"}],
            "missing_values": ["", "NA"], "synthetic": True}


class DocxTests(unittest.TestCase):
    def test_hyphen_elements_do_not_join_numeric_range(self):
        result = imp.extract_docx(docx('<w:p><w:r><w:t>10</w:t><w:noBreakHyphen/><w:t>20</w:t></w:r></w:p>'))
        self.assertEqual(result["blocks"][0]["text"], "10\u201120")

    def test_tracked_moves_rejected(self):
        body = '<w:p><w:moveFrom><w:r><w:t>OLD</w:t></w:r></w:moveFrom><w:moveTo><w:r><w:t>NEW</w:t></w:r></w:moveTo></w:p>'
        with self.assertRaises(imp.MaterialError):
            imp.extract_docx(docx(body))

    def test_order_and_cell_coordinates(self):
        body = paragraph("Первый") + "<w:tbl><w:tr><w:tc>" + paragraph("Ячейка") + paragraph("Вторая строка") + "</w:tc></w:tr></w:tbl>" + paragraph("Последний")
        result = imp.extract_docx(docx(body))
        self.assertEqual([b["kind"] for b in result["blocks"]], ["paragraph", "table", "paragraph"])
        self.assertEqual(result["blocks"][1]["rows"][0][0]["paragraphs"][1],
                         {"locator": "body/b2/t1/r1/c1/p2", "text": "Вторая строка"})
        self.assertEqual(result["blocks"][2]["locator"], "body/b3/p2")
        self.assertNotIn("page", result["blocks"][2])

    def test_unsupported_changes_not_silently_omitted(self):
        for body in ("<w:ins>" + paragraph("Правка") + "</w:ins>",
                     "<w:tbl><w:tr><w:tc><w:tbl/></w:tc></w:tr></w:tbl>",
                     "<w:p><w:r><w:drawing/></w:r></w:p>"):
            with self.subTest(body=body), self.assertRaises(imp.MaterialError):
                imp.extract_docx(docx(body))

    def test_unpack_guard(self):
        with self.assertRaises(imp.MaterialError):
            imp.extract_docx(docx(paragraph("x" * 100)), max_unpacked=20)

    def test_xml_entities_refused(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as z:
            z.writestr("word/document.xml", '<!DOCTYPE document [<!ENTITY a "x">]><document>&a;</document>')
        with self.assertRaises(imp.MaterialError):
            imp.extract_docx(buffer.getvalue())


class CsvTests(unittest.TestCase):
    def test_large_precision_input_rejected_before_early_rounding(self):
        raw = b"period,segment,eligible,retained\n2026-09,a,100000000000000000000000000000000,494999999999999999999999999999\n"
        with self.assertRaisesRegex(imp.MaterialError, "технический предел"):
            calc.calculate(raw, specification())

    def test_exact_rounding_near_half_boundary(self):
        from decimal import Decimal, localcontext
        # Regression independent of ambient Decimal precision or half-way rounding.
        with localcontext() as context:
            context.prec = 8
            self.assertEqual(calc.rounded_value(Decimal("494999999999999999999999999999"),
                                               Decimal("100000000000000000000000000000000"), Decimal(100), 2), "0.49")
            self.assertEqual(calc.rounded_value(Decimal("-1.235"), Decimal(1), Decimal(1), 2), "-1.24")
            self.assertEqual(calc.exact_sum([Decimal("100000000000000000"), Decimal("0.000000000001")]),
                             Decimal("100000000000000000.000000000001"))

    def test_weighted_ratio_not_mean_of_ratios(self):
        result = calc.calculate(b"period,segment,eligible,retained\n2026-09,a,10,5\n2026-09,a,90,9\n", specification())
        metric = result["groups"][0]["metrics"]["retention"]
        self.assertEqual(metric["value"], "14.00")
        self.assertEqual(metric["numerator"], "14")
        self.assertEqual(metric["denominator"], "100")
        self.assertEqual(metric["unit"], "%")
        self.assertTrue(result["synthetic"])

    def test_missing_not_zero_and_zero_denominator(self):
        raw = b"period,segment,eligible,retained\n2026-09,a,10,\n2026-09,a,90,9\n2026-09,b,0,0\n"
        groups = calc.calculate(raw, specification())["groups"]
        self.assertIsNone(groups[0]["metrics"]["retention"]["value"])
        self.assertEqual(groups[0]["metrics"]["retention"]["status"], "missing")
        self.assertEqual(groups[1]["metrics"]["retention"]["status"], "zero_denominator")

    def test_bad_numeric_and_domain_inputs_rejected(self):
        for values in ("10,11", "10,NaN", "10,1.1", "10,=SUM(A1)", "-1,0", "10,Infinity", ",1,2"):
            with self.subTest(values=values), self.assertRaises(imp.MaterialError):
                calc.calculate(("period,segment,eligible,retained\n2026-09,a," + values + "\n").encode(), specification())

    def test_period_and_unit_mismatch_rejected(self):
        raw = b"period,segment,eligible,retained\n2026-09,a,10,5\n"
        bad = specification()
        bad["group_by"] = ["segment"]
        with self.assertRaises(imp.MaterialError):
            calc.calculate(raw, bad)
        bad = specification()
        bad["columns"]["retained"]["unit"] = "RUB"
        with self.assertRaises(imp.MaterialError):
            calc.calculate(raw, bad)

    def test_physical_csv_lines_include_multiline_cell(self):
        parsed = imp.read_csv_bytes(b'name,value\n"two\nlines",2\nend,3\n')
        self.assertEqual(parsed["rows"][0]["locator"], "rows:2-3")
        self.assertEqual(parsed["rows"][1]["locator"], "rows:4-4")

    def test_duplicate_header_and_row_limit(self):
        for raw, limit in ((b"a,a\n1,2\n", 10), (b"a\n1\n2\n", 1)):
            with self.assertRaises(imp.MaterialError):
                imp.read_csv_bytes(raw, max_rows=limit)


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "inputs").mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_reuse_revision_and_old_original_retained(self):
        path = self.root / "inputs/test.txt"
        path.write_text("one", encoding="utf-8")
        first = imp.register(self.root, "S001", "inputs/test.txt", "text", synthetic=True)
        again = imp.register(self.root, "S001", "inputs/test.txt", "text", synthetic=True)
        self.assertTrue(again["reused"])
        self.assertEqual(first["record"], again["record"])
        # Identical bytes but changed provenance must produce a new meaningful version.
        second = imp.register(self.root, "S001", "inputs/test.txt", "text", synthetic=False)
        self.assertEqual(second["source"]["version"], 2)
        path.write_text("two", encoding="utf-8")
        third = imp.register(self.root, "S001", "inputs/test.txt", "text", synthetic=False)
        self.assertEqual(third["source"]["version"], 3)
        self.assertEqual((self.root / first["source"]["original"]["path"]).read_text(), "one")

    def test_corrupt_registered_extract_is_visible(self):
        (self.root / "inputs/test.txt").write_text("one", encoding="utf-8")
        first = imp.register(self.root, "S001", "inputs/test.txt", "text")
        (self.root / first["source"]["extract"]["path"]).write_text("bad", encoding="utf-8")
        with self.assertRaises(imp.MaterialError):
            imp.register(self.root, "S001", "inputs/test.txt", "text")

    def test_incomplete_import_is_reported(self):
        (self.root / "inputs/test.txt").write_text("one", encoding="utf-8")
        (self.root / "evidence/sources/S001/v1").mkdir(parents=True)
        result = imp.register(self.root, "S001", "inputs/test.txt", "text")
        self.assertEqual(result["source"]["version"], 2)
        self.assertEqual(result["incomplete_versions"], ["evidence/sources/S001/v1"])

    def test_paths_and_ids_do_not_escape_project(self):
        (self.root / "inputs/test.txt").write_text("one", encoding="utf-8")
        with self.assertRaises(imp.MaterialError):
            imp.register(self.root, "../escape", "inputs/test.txt", "text")
        with self.assertRaises(imp.MaterialError):
            imp.scoped(self.root, "../escape", must_exist=False)

    def test_existing_version_symlink_cannot_read_outside_metadata(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as outside:
            external = Path(outside)
            (external / "source.json").write_text("{}", encoding="utf-8")
            (self.root / "inputs/test.txt").write_text("one", encoding="utf-8")
            folder = self.root / "evidence/sources/S001"
            folder.mkdir(parents=True)
            try:
                (folder / "v1").symlink_to(external, target_is_directory=True)
            except OSError:
                self.skipTest("Хост не разрешает создание directory symlink")
            actual_read = Path.read_text
            external_reads = []

            def tracked_read(path, *args, **kwargs):
                if path.resolve().is_relative_to(external):
                    external_reads.append(path)
                return actual_read(path, *args, **kwargs)

            with patch.object(Path, "read_text", tracked_read):
                with self.assertRaises(imp.MaterialError):
                    imp.register(self.root, "S001", "inputs/test.txt", "text")
            self.assertEqual(external_reads, [])
            self.assertFalse((folder / "v2").exists())

    def test_web_requires_actual_provenance_fields(self):
        (self.root / "inputs/page.txt").write_text("Short excerpt", encoding="utf-8")
        with self.assertRaises(imp.MaterialError):
            imp.register(self.root, "WEB", "inputs/page.txt", "web-excerpt", origin="https://example.com")
        result = imp.register(self.root, "WEB", "inputs/page.txt", "web-excerpt", origin="https://example.com",
                              accessed_at="2026-11-16T09:00:00+03:00", locator="section: Features",
                              retrieval_status="supplied_snapshot")
        self.assertEqual(result["source"]["retrieval_status"], "supplied_snapshot")
        self.assertIn("host-rendered-excerpt", result["source"]["extraction_method"])

    def test_calculation_bound_to_version_and_synthetic_propagates(self):
        raw = b"period,segment,eligible,retained\n2026-09,a,10,5\n"
        (self.root / "inputs/data.csv").write_bytes(raw)
        imp.register(self.root, "S002", "inputs/data.csv", "csv", synthetic=True)
        spec = specification()
        spec["synthetic"] = False
        (self.root / "inputs/spec.json").write_text(json.dumps(spec), encoding="utf-8")
        result = calc.run(self.root, "inputs/data.csv", "inputs/spec.json", "evidence/calc1.json", source_id="S002", source_version=1)
        self.assertTrue(result["result"]["synthetic"])
        with self.assertRaises(imp.MaterialError):
            calc.run(self.root, "inputs/data.csv", "inputs/spec.json", "evidence/calc1.json", source_id="S002", source_version=1)
        (self.root / "inputs/data.csv").write_bytes(raw.replace(b",5", b",4"))
        with self.assertRaises(imp.MaterialError):
            calc.run(self.root, "inputs/data.csv", "inputs/spec.json", "evidence/calc2.json", source_id="S002", source_version=1)


if __name__ == "__main__":
    unittest.main()
