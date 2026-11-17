# Ordinary baseline: NOT_RUN

Новой пары ответов нет. TASK05 frozen-v2 сохраняется PRE-FIX; его ablation A/B′ не смешивается с текущим кодом. Новый freeze `ordinary-current-v1` содержит исходную предметную историю/три запроса TASK05 и текущие corrected scripts/knowledge/AGENTS у A. У обоих одинаковая переносимая установка из wheels и явное UTF-8 чтение. Изменения протокола закреплены **до** будущего запуска в `ordinary-freeze-manifest.json`; разница версии не скрывается.

При появлении поддержанного маршрута подготовить две новые папки вне ancestry Megafon AGENTS существующей утилитой:

```powershell
.\.venv\Scripts\python.exe -X utf8 evaluation/task06/ordinary_handoff.py prepare --condition A --workspace "$env:TEMP\task06-ordinary-A-01"
.\.venv\Scripts\python.exe -X utf8 evaluation/task06/ordinary_handoff.py prepare --condition B --workspace "$env:TEMP\task06-ordinary-B-01"
```

В двух независимых answer-blind чатах выполнить одинаковый bootstrap: «Прочитай request-q1.txt и RUNTIME.md как UTF-8 и выполни запрос; работай только в этой папке». Зафиксировать наблюдаемые инструкции, модель/настройки, tools и неизвестные различия. Если B наследует Megafon guidance, ordinary B остаётся NOT_RUN: новый каталог/отсутствие истории недостаточны. Глобальные инструкции/разрешения сохраняются.

После **обоих первых ответов** выдать q2 командой `stage --phase q2`, затем q3. Сохранять первые ответы, историю каждой стороны, failures/retries/interventions через `snapshot` и raw logs. Команды те же, что в [TASK05 README](../task05/README.md), но launcher — `evaluation/task06/ordinary_handoff.py`, output — новый `evaluation/task06/ordinary-run-01/...`.

Оценщик получает [rubric-v1.json](../task05/rubric-v1.json) и [expectations-v1.json](../task05/expectations-v1.json) после ответов. Участникам эти файлы не передаются. Не требовать от B схемы A; проверять факты, полезность, затронутые/незатронутые выводы, authority и реальную сохранность. Координатор, знающий ответы, не становится измеряемым участником. Автоматическое review и малый sample ограничивают выводы; tie допустим. Этот дополнительный тест не блокирует локальный пакет.
