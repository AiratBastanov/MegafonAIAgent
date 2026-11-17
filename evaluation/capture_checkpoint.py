"""Снять чистую копию реально незавершённого проекта для отдельного host.

Никаких finished answers, evaluator files, credentials или .venv в копии.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.project_state import load_state


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--project-id",required=True);p.add_argument("--workspace",type=Path,required=True)
    p.add_argument("--archive",type=Path,required=True);p.add_argument("--manifest",type=Path,required=True)
    runtime_group=p.add_mutually_exclusive_group(required=True)
    runtime_group.add_argument("--python",type=Path)
    runtime_group.add_argument("--portable",action="store_true",help="Создать инструкции новой .venv без абсолютного interpreter")
    a=p.parse_args();project=ROOT/"projects"/a.project_id
    if project.resolve().parent!=(ROOT/"projects").resolve():raise ValueError("Недопустимый project ID")
    s=load_state(project)
    if (project/"outputs").exists():raise ValueError("Снимок до синтеза не должен содержать outputs")
    for dest in (a.workspace,a.archive,a.manifest):
        resolved=dest.resolve()
        if not resolved.is_relative_to(ROOT) or resolved==ROOT or dest.exists():raise ValueError("Нужен новый путь внутри workspace")
    paths=[ROOT/"AGENTS.md",ROOT/"requirements.txt"]
    paths+=list((ROOT/"knowledge").rglob("*.md"))+list((ROOT/"scripts").glob("*.py"))
    if a.portable:
        paths+=[f for f in (ROOT/"third_party/wheels").glob("*") if f.is_file()]
        paths.append(ROOT/"evaluation/calc_offer_scenarios.py")
    paths+=[f for f in project.rglob("*") if f.is_file() and "__pycache__" not in f.parts]
    a.workspace.mkdir(parents=True,exist_ok=False)
    for source in paths:
        if not source.resolve().is_relative_to(ROOT):raise ValueError("Источник выходит за workspace")
        target=a.workspace/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    interpreter=a.python.resolve(strict=True) if a.python else None
    runtime=("# Переносимая среда handoff\n\n"
             "В новой папке распаковки, PowerShell, Python 3.12:\n\n"
             "```powershell\npython -m venv .venv\n"
             ".\\.venv\\Scripts\\python.exe -m pip install --no-index --find-links third_party/wheels -r requirements.txt\n```\n\n"
             "После установки используй `.\\.venv\\Scripts\\python.exe -X utf8`. "
             "Читай текст через `Get-Content -Encoding UTF8`. "
             "Нужен уже авторизованный Codex host с локальными tools; Python сам не выполняет анализ LLM. "
             "Работай только в этой копии. Исходная беседа, поздние outputs и evaluator notes не предоставлены.\n") if a.portable else ("# Среда этой проверочной копии\n\n"
             f"Проверенный interpreter: `{interpreter}`. Используй этот Python либо `python` из PATH launcher. "
             "Python 3.12.10; openpyxl 3.1.5, pypdf 7.1.0, et-xmlfile 2.0.0. "
             "Окружение находится в исходном разрешённом workspace и явно переиспользуется; .venv сюда не копировалась. "
             "Для переноса создать новую .venv и pip install -r requirements.txt.\n"
             "Читай/изменяй проект только внутри этой копии. Исходный workspace, журналы оценки и другие проекты не входят в задачу продолжения. "
             "Этот файл описывает среду, не содержит результата продуктового анализа.\n")
    (a.workspace/"RUNTIME.md").write_text(runtime,encoding="utf-8")
    with (a.workspace/"AGENTS.md").open("a",encoding="utf-8") as file:
        file.write("\nСреда изолированной копии: сначала прочитай `RUNTIME.md`; работай только с локальным проектом этой копии.\n")
    files=[]
    for file in sorted(a.workspace.rglob("*")):
        if file.is_file():files.append({"path":file.relative_to(a.workspace).as_posix(),"sha256":hashlib.sha256(file.read_bytes()).hexdigest(),"size":file.stat().st_size})
    with zipfile.ZipFile(a.archive,"x",compression=zipfile.ZIP_DEFLATED) as archive:
        for item in files:archive.write(a.workspace/item["path"],item["path"])
    record={"captured_at":datetime.now(timezone.utc).isoformat(),"project_id":a.project_id,"starting_revision":s["revision"],
            "starting_stage":s["stage"],"state_sha256":s["state_sha256"],"workspace":a.workspace.as_posix(),
            "archive":a.archive.as_posix(),"archive_sha256":hashlib.sha256(a.archive.read_bytes()).hexdigest(),
            "no_outputs_at_capture":True,"no_evaluator_answers_or_transcript_supplied":True,
            "python":str(interpreter) if interpreter else None,"portable_setup":a.portable,"files":files}
    a.manifest.write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"revision":s["revision"],"files":len(files),"captured_at":record["captured_at"]}))
