"""Независимая Fraction-проверка собственного demo-002 по raw OOXML.

Не импортирует analyze_table или сценарный калькулятор.
"""
import argparse
from datetime import datetime,timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import zipfile
from xml.etree import ElementTree as ET

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def cells(path,sheet):
    with zipfile.ZipFile(path) as z:
        root=ET.fromstring(z.read(f"xl/worksheets/sheet{sheet}.xml"))
    ns={"x":"http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    return {c.attrib["r"]:Fraction(c.find("x:v",ns).text) for c in root.findall(".//x:c",ns)
            if c.attrib.get("t")=="n" and c.find("x:v",ns) is not None and c.find("x:v",ns).text and c.find("x:f",ns) is None}

def check(project,version):
    p=Path(project);fpath=p/"evidence/calculations/funnel-v1.json";epath=p/f"evidence/calculations/economics-v{version}.json"
    funnel=json.loads(fpath.read_text(encoding="utf-8"));economics=json.loads(epath.read_text(encoding="utf-8"))
    fbook=p/f"evidence/sources/S002/v{funnel['source']['version']}/original.xlsx"
    ebook=p/f"evidence/sources/S002/v{economics['source']['version']}/original.xlsx"
    assert digest(fbook)==funnel["input"]["sha256"] and digest(ebook)==economics["input"]["sha256"]
    values=cells(fbook,1);checks=[]
    for row,group in zip((3,4),funnel["groups"]):
        for name,n,d in (("paid_per_trial_pct","F","D"),("interest_per_trial_pct","E","D"),("paid_per_contact_pct","F","C")):
            metric=group["metrics"][name];expected=values[f"{n}{row}"]/values[f"{d}{row}"]*100
            assert Fraction(metric["value"])==expected
            checks.append({"kind":"funnel","locator":f"'Воронка'!{n}{row}/{d}{row}","metric":name,"exact":str(expected),"pass":True})
        assert group["metrics"]["acquisition"]["value"] is None and group["metrics"]["acquisition"]["status"]=="missing"
    raw=cells(ebook,2)
    for scenario in [economics["base"],*economics["scenarios"]]:
        minutes=Fraction(scenario["support_minutes"]);accounts=Fraction(scenario["accounts"])
        margin=raw["C3"]-raw["D3"]-minutes*raw["F3"]/60;surplus=accounts*margin-raw["G3"]
        assert Fraction(scenario["margin_rub_per_account_month"])==margin
        assert Fraction(scenario["surplus_before_unknown_costs_rub_month"])==surplus
        threshold=raw["G3"]/margin if margin>0 else None
        nonnegative=-(-threshold.numerator//threshold.denominator) if threshold is not None else None
        positive=threshold.numerator//threshold.denominator+1 if threshold is not None else None
        assert scenario["min_accounts_nonnegative"]==nonnegative and scenario["min_accounts_positive"]==positive
        payback=scenario["conditional_setup_payback_months"]
        if surplus<=0:assert payback is None
        else:assert abs(Fraction(payback)-raw["H3"]/surplus)<Fraction(1,10**20)
        checks.append({"kind":"scenario","minutes":str(minutes),"accounts":str(accounts),"margin":str(margin),"surplus":str(surplus),"pass":True})
    assert Fraction(economics["base"]["support_minutes"])==raw["E3"]
    return {"checked_at":datetime.now(timezone.utc).isoformat(),"method":"zipfile+ElementTree raw numeric OOXML; fractions.Fraction, independent formulas",
            "synthetic":True,"funnel_source_version":funnel["source"]["version"],"economics_source_version":economics["source"]["version"],
            "funnel_sha256":digest(fpath),"economics_sha256":digest(epath),"checks":checks,"passed":True}

if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--project",type=Path,required=True);ap.add_argument("--version",type=int,required=True);ap.add_argument("--output",required=True)
    a=ap.parse_args();result=check(a.project,a.version)
    with (a.project/a.output).open("x",encoding="utf-8") as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({"passed":True,"checks":len(result["checks"])}))
