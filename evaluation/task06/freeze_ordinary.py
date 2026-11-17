"""Prepare a new, unexecuted pair using TASK05's inputs and corrected current code."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
source=ROOT/'evaluation/task05/frozen-v2'
dest=HERE/'ordinary-current-v1'
if dest.exists():raise FileExistsError(dest)
shutil.copytree(source,dest,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for component in ('scripts','knowledge'):
    for p in (ROOT/component).rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:
            target=dest/'A'/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
for name in ('AGENTS.md','requirements.txt'):
    shutil.copyfile(ROOT/name,dest/'A'/name)
runtime='''# Среда новой, ещё не исполненной пары TASK06

Работать только в назначенной папке. Тексты читать UTF-8. Из корня папки:

```powershell
python -m venv .venv
.\\.venv\\Scripts\\python.exe -m pip install --no-index --find-links third_party/wheels -r requirements.txt
```

Python 3.12; версии закреплены. Старое окружение не копируется.
Команды можно сохранять через `capture.py logs UNIQUE_LABEL -- EXECUTABLE ARGS...`.
Первый ответ и метаданные сохраняются в responses; будущие prompts выдаются по очереди.
Нужен независимый разрешённый Codex-контекст; настройки/инструкции фиксируются по факту.
Этот пакет не создаёт LLM-сессию и не подтверждает отсутствие inherited guidance.
'''
for condition in ('A','B'):
    (dest/condition/'RUNTIME.md').write_text(runtime,encoding='utf-8')
    shutil.copyfile(ROOT/'requirements.txt',dest/condition/'requirements.txt')
    shutil.copytree(ROOT/'third_party',dest/condition/'third_party')
files={p.relative_to(dest).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.rglob('*')) if p.is_file()}
record={'created_at':datetime.now(timezone.utc).isoformat(),'status':'NOT_RUN','prior_freeze':'evaluation/task05/frozen-v2',
    'changes':['A current corrected scripts/knowledge/AGENTS; pinned dependency files',
               'Both conditions: portable offline runtime and same wheels; UTF-8 instructions'],
    'unchanged':'Business inputs, neutral context, three requests and events copied byte-for-byte; no measured responses or grading notes added.',
    'model_id':None,'settings':None,'files':files}
with (HERE/'ordinary-freeze-manifest.json').open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2)
print(json.dumps({'status':'NOT_RUN','files':len(files)}))
