# Runtime и наблюдения

Python: `C:\Users\BastaPC\Desktop\MegafonAIAgent\.venv\Scripts\python.exe` (существующая проектная .venv, не скопирована).
Рабочая папка — текущий package root. Чтение RUNTIME.md и исходного prompt допускается напрямую как bootstrap.
Команды выполняй из package root через общий generic capture:

```powershell
& "C:\Users\BastaPC\Desktop\MegafonAIAgent\.venv\Scripts\python.exe" -X utf8 capture.py logs q1-read -- powershell -NoProfile -Command "Get-Content -Encoding UTF8 context.md"
```

Каждый LABEL новый. Можно вызывать Python с -X utf8 и -c для чтения/арифметики/записи файлов. capture сохраняет команду, cwd, stdout/stderr, exit, начало/конец/elapsed. Запись артефактов через apply_patch допустима; перечисли такие записи в meta. Изменения источников и старых ответов запрещены; новые outputs/notes получают новые пути. Не читай соседние каталоги. История своего контекста и собственные заметки сохраняются между шагами.
