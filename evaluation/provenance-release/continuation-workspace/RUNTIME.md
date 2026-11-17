# Переносимая среда handoff

В новой папке распаковки, PowerShell, Python 3.12:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-index --find-links third_party/wheels -r requirements.txt
```

После установки используй `.\.venv\Scripts\python.exe -X utf8`. Читай текст через `Get-Content -Encoding UTF8`. Нужен уже авторизованный Codex host с локальными tools; Python сам не выполняет анализ LLM. Работай только в этой копии. Исходная беседа, поздние outputs и evaluator notes не предоставлены.
