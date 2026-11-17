"""Сквозные риски XLSX → явная арифметика → state без смены schema_version."""
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from openpyxl import Workbook

from scripts import analyze_table as calc, import_materials as imp, project_state as state


class XlsxCalculationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / "case-two"
        (self.project / "inputs").mkdir(parents=True)
        self.spec = {
            "columns": {"period": {"type":"text","unit":"month"}, "eligible":{"type":"integer","unit":"accounts"},
                        "paid":{"type":"integer","unit":"accounts"}, "cost":{"type":"decimal","unit":"RUB"}},
            "group_by":["period"], "period_column":"period", "missing_values":[""], "synthetic":False,
            "metrics":[{"id":"conversion","operation":"ratio","numerator":["paid"],"denominator":["eligible"],
                        "multiplier":"100","unit":"%","rounding":2},
                       {"id":"cost","operation":"sum","numerator":["cost"],"unit":"RUB","rounding":2}],
            "xlsx":{"sheet":"Лист 'оригинал'","rows":[2,3],"columns":{"period":"A","eligible":"B","paid":"C","cost":"D"},
                    "include_hidden":False}}
        self.selection = {"ranges":[{"sheet":"Лист 'оригинал'","range":"A1:E3","period":"2026-09",
                                      "units":{"A":"month","B":"accounts","C":"accounts","D":"RUB","E":"ratio"}}]}
        self.write_json("inputs/selection.json", self.selection)
        self.write_json("inputs/spec.json", self.spec)

    def write_json(self, path, value):
        (self.project / path).write_bytes(imp.json_bytes(value))

    def workbook(self, name="v1", paid=5, formula=False, hidden=False, merged=False):
        wb=Workbook(); ws=wb.active; ws.title="Лист 'оригинал'"
        ws.append(["month","eligible","paid","cost","formula"])
        ws.append(["2026-09",10,"=B2/2" if formula else paid,100,"=C2/B2"])
        ws.append(["2026-09",90,9,None,"=C3/B3"])
        ws.row_dimensions[2].hidden=hidden
        if merged:ws.merge_cells("B2:B3")
        buf=io.BytesIO();wb.save(buf)
        path=f"inputs/{name}.xlsx"; (self.project/path).write_bytes(buf.getvalue())
        registration=imp.register(self.project,"S001",path,"xlsx",synthetic=True,selection_path="inputs/selection.json")
        return path, registration

    def run_calc(self, path, version=1, name="v1"):
        return calc.run(self.project,path,"inputs/spec.json",f"evidence/calc-{name}.json",source_id="S001",source_version=version)

    def test_coordinates_units_missing_and_lineage_survive_state_reload(self):
        path, registered=self.workbook(); result=self.run_calc(path)["result"]
        metric=result["groups"][0]["metrics"]
        self.assertEqual(metric["conversion"]["value"],"14.00")
        self.assertEqual(metric["conversion"]["denominator"],"100")
        self.assertIsNone(metric["cost"]["value"])
        self.assertEqual(metric["cost"]["missing"],[{"locator":"'Лист ''оригинал'''!D3","column":"cost"}])
        self.assertTrue(result["synthetic"])
        self.assertIn("'Лист ''оригинал'''!C2",result["groups"][0]["locators"][0])
        self.assertEqual(result["provenance"]["source_type"],"xlsx")
        refs=[state.reference(self.project,registered["record"]["path"],"META"),
              state.reference(self.project,registered["source"]["original"]["path"],"ORIGINAL"),
              state.reference(self.project,registered["source"]["extract"]["path"],"EXTRACT"),
              state.reference(self.project,"inputs/spec.json","SPEC"),
              state.reference(self.project,"evidence/calc-v1.json","CALC")]
        draft={"schema_version":1,"project_id":"case-two","objective":"Проверить конверсию",
               "decision_question":"Продолжать ли?","stage":"research","completed":["Расчёт"],
               "pending_actions":["Проверить спрос"],"unresolved_questions":["Расходы"],"next_action":"Проверить спрос",
               "artifacts":refs,"sources":[{"id":"S001","version":1,"synthetic":True,"artifact_ids":["META","ORIGINAL","EXTRACT"]}],
               "claims":[{"id":"C001","kind":"computed","text":"14 процентов","synthetic":True,"derived_from":[],
                          "evidence":[{"artifact_id":"CALC","source_id":"S001","source_version":1,"locator":"groups[0].metrics.conversion"}]}],
               "decision":{"status":"proposed"}}
        state.save_state(self.project,draft)
        self.assertEqual(state.load_state(self.project)["claims"][0]["text"],"14 процентов")
        bad=copy.deepcopy(draft);bad["claims"][0]["synthetic"]=False
        with self.assertRaises(state.StateError):state.validate_state(self.project,bad)

    def test_formula_and_hidden_rows_are_not_silently_used(self):
        path,_=self.workbook(formula=True)
        with self.assertRaisesRegex(imp.MaterialError,"формула"):self.run_calc(path)
        path,_=self.workbook("v2",hidden=True)
        with self.assertRaisesRegex(imp.MaterialError,"скрыта"):self.run_calc(path,2)
        self.spec["xlsx"]["include_hidden"]=True;self.write_json("inputs/spec.json",self.spec)
        self.assertEqual(self.run_calc(path,2)["result"]["groups"][0]["metrics"]["conversion"]["value"],"14.00")

    def test_version_binding_correction_and_original_preservation(self):
        path,first=self.workbook(); original=(self.project/path).read_bytes()
        self.assertEqual(self.run_calc(path)["result"]["groups"][0]["metrics"]["conversion"]["value"],"14.00")
        changed,second=self.workbook("v2",paid=3)
        with self.assertRaisesRegex(imp.MaterialError,"не совпадает"):self.run_calc(changed,1,"wrong")
        self.assertEqual(self.run_calc(changed,2,"v2")["result"]["groups"][0]["metrics"]["conversion"]["value"],"12.00")
        self.assertEqual(original,(self.project/first["source"]["original"]["path"]).read_bytes())
        self.assertFalse((self.project/"evidence/calc-wrong.json").exists())

    def test_units_period_merged_and_extract_corruption_fail_explicitly(self):
        path,registered=self.workbook()
        self.spec["columns"]["cost"]["unit"]="USD";self.write_json("inputs/spec.json",self.spec)
        with self.assertRaisesRegex(imp.MaterialError,"единица"):self.run_calc(path)
        self.spec["columns"]["cost"]["unit"]="RUB"
        self.spec["xlsx"]["rows"]=[1];self.write_json("inputs/spec.json",self.spec)
        with self.assertRaisesRegex(imp.MaterialError,"период"):self.run_calc(path)
        self.spec["xlsx"]["rows"]=[2,3];self.write_json("inputs/spec.json",self.spec)
        merged,_=self.workbook("merged",merged=True)
        with self.assertRaisesRegex(imp.MaterialError,"объединение"):self.run_calc(merged,2,"merged")
        (self.project/registered["source"]["extract"]["path"]).write_text("{}",encoding="utf-8")
        with self.assertRaisesRegex(imp.MaterialError,"Повреждена"):self.run_calc(path)

    def test_different_periods_in_disjoint_ranges_cannot_be_combined(self):
        self.selection["ranges"]=[
            {"sheet":"Лист 'оригинал'","range":"A1:C3","period":"2026-09","units":{"A":"month","B":"accounts","C":"accounts"}},
            {"sheet":"Лист 'оригинал'","range":"D1:D3","period":"2026-10","units":{"D":"RUB"}}]
        self.write_json("inputs/selection.json",self.selection)
        path,_=self.workbook()
        with self.assertRaisesRegex(imp.MaterialError,"разные или неизвестные периоды"):self.run_calc(path)


if __name__=="__main__":unittest.main()
