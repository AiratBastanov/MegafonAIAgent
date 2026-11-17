# Среда новой, ещё не исполненной пары TASK06

Работать только в назначенной папке. Тексты читать UTF-8. Из корня папки:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-index --find-links third_party/wheels -r requirements.txt
```

Python 3.12; версии закреплены. Старое окружение не копируется.
Команды можно сохранять через `capture.py logs UNIQUE_LABEL -- EXECUTABLE ARGS...`.
Первый ответ и метаданные сохраняются в responses; будущие prompts выдаются по очереди.
Нужен независимый разрешённый Codex-контекст; настройки/инструкции фиксируются по факту.
Этот пакет не создаёт LLM-сессию и не подтверждает отсутствие inherited guidance.
