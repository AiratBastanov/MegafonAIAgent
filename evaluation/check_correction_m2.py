"""Проверить границу коррекции, сохранность прошлых state и изоляцию demo-001."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.project_state import validate_state,load_state
from scripts.import_materials import write_new,json_bytes


if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
    project=Path("projects/demo-002")
    extracts=[json.loads((project/f"evidence/sources/S002/v{v}/extract.json").read_text(encoding="utf-8")) for v in (1,2)]
    maps=[{(s["name"],c["address"]):c for s in e["sheets"] for c in s["cells"]} for e in extracts]
    assert set(maps[0])==set(maps[1])
    changes=[{"sheet":key[0],"address":key[1],"before":maps[0][key],"after":maps[1][key]} for key in maps[0] if maps[0][key]!=maps[1][key]]
    assert len(changes)==1 and (changes[0]["sheet"],changes[0]["address"])==("Экономика","E3")
    assert changes[0]["before"]["value"]==30 and changes[0]["after"]["value"]==90
    versions=[]
    for path in sorted((project/"state/history").glob("r*.json")):
        state=json.loads(path.read_text(encoding="utf-8"));validate_state(project,state,require_saved=True);versions.append(state["revision"])
    baseline=json.loads(Path("evaluation/task03/demo001-baseline-manifest.json").read_text(encoding="utf-8"))
    current={p.relative_to(Path("projects/demo-001")).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
             for p in Path("projects/demo-001").rglob("*") if p.is_file()}
    assert current==baseline["files"]
    m1=load_state("projects/demo-001");assert m1["revision"]==5
    funnel=json.loads((project/"evidence/calculations/funnel-v1.json").read_text(encoding="utf-8"))
    assert funnel["source"]=={"id":"S002","version":1}
    result={"checked_at":datetime.now(timezone.utc).isoformat(),"changes":changes,"changed_selected_cells":1,
            "funnel_reused_from_source_version":1,"funnel_reuse_reason":"Воронка не изменилась; изменено только сценарное E3 другого листа",
            "historical_demo002_revisions_validated":versions,"demo001_revision":m1["revision"],
            "demo001_files_unchanged":len(current),"demo001_manifest_match":True,"passed":True}
    write_new(a.output,json_bytes(result));print(json.dumps({"passed":True,"changed_cells":1,"demo001_unchanged_files":len(current),"historical_revisions":versions}))
