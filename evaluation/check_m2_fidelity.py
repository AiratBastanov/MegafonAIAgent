"""Проверка собственных M2 fixtures по исходным PDF bytes/OOXML, не PDF/XLSX parser.

Ограничена известным макетом генератора; не заявляет визуальную приёмку.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import zipfile
from xml.etree import ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.import_materials import sha256, write_new, json_bytes


def verify(project,version):
    project=Path(project); records={}
    for sid,v in (("S001",1),("S002",version)):
        folder=project/f"evidence/sources/{sid}/v{v}"
        meta=json.loads((folder/"source.json").read_text(encoding="utf-8"))
        original=project/meta["original"]["path"]; extracted=project/meta["extract"]["path"]
        assert sha256(original.read_bytes())==meta["input_sha256"]==meta["original"]["sha256"]
        assert sha256(extracted.read_bytes())==meta["extract"]["sha256"]
        records[sid]=(meta,original,json.loads(extracted.read_text(encoding="utf-8")))
    manifest=json.loads((project/"inputs/pdf-text-manifest-v1.json").read_text(encoding="utf-8"))
    pdf_meta,pdf_file,pdf_extract=records["S001"]; raw=pdf_file.read_bytes();checks=[]
    assert len(manifest["physical_pages"])==len(pdf_extract["pages"])==2
    for expected,page in zip(manifest["physical_pages"],pdf_extract["pages"]):
        actual=[line.strip() for line in page["text"].splitlines() if line.strip()]
        assert actual==expected["lines"], (expected["page"],actual)
        assert page["physical_page"]==expected["page"] and page["page_label"]==expected["label"]
        assert not page["layout_warnings"]
        for index,line in enumerate(expected["lines"],1):
            encoded=line.replace("\\","\\\\").replace("(","\\(").replace(")","\\)").encode("ascii")
            assert b"("+encoded+b") Tj" in raw
            checks.append({"source":"S001@1","physical_page":expected["page"],"expected_line":index,
                           "text":line,"source_literal_verified":True,"extraction_complete_for_line":True})
    wb_meta,wb_file,wb_extract=records["S002"]
    ns={"x":"http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(wb_file) as archive:
        for index,name in ((1,"Воронка"),(2,"Экономика")):
            xml=ET.fromstring(archive.read(f"xl/worksheets/sheet{index}.xml"))
            source={c.attrib["r"]:c for c in xml.findall(".//x:c",ns)}
            sheet=next(s for s in wb_extract["sheets"] if s["name"]==name)
            cells={c["address"]:c for c in sheet["cells"]}
            addresses=[f"{c}{r}" for c in ("CDEFGH" if index==1 else "CDEFGHI") for r in ((3,4) if index==1 else (3,))]
            for address in addresses:
                assert source[address].attrib.get("t")=="n"
                original_value=source[address].find("x:v",ns).text
                assert str(cells[address]["value"])==original_value
                checks.append({"source":f"S002@{version}","locator":cells[address]["locator"],
                               "original_xml_value":original_value,"extract_value":cells[address]["value"],"pass":True})
        assert next(c for s in wb_extract["sheets"] if s["name"]=="Воронка" for c in s["cells"] if c["address"]=="I3")["value"] is None
    return {"checked_at":datetime.now(timezone.utc).isoformat(),"synthetic":True,
            "method":"Полный PDF text manifest + literal bytes собственного генератора; decisive XLSX values сверены с raw OOXML ET, не результатом openpyxl",
            "pdf_sha256":pdf_meta["input_sha256"],"xlsx_sha256":wb_meta["input_sha256"],"xlsx_source_version":version,
            "visual_layout_verified":False,"market_validation":False,"checks":checks,"passed":True}


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--project",type=Path,required=True);p.add_argument("--version",type=int,default=1);p.add_argument("--output",required=True)
    a=p.parse_args();result=verify(a.project,a.version);write_new(a.project/a.output,json_bytes(result))
    print(json.dumps({"passed":True,"checks":len(result["checks"]),"visual_layout_verified":False}))
