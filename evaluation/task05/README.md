# TASK05: воспроизведение узкого follow-up

Рабочие входы — `frozen-v2`, точные prompts — `frozen-v2/prompts/A|B/q1.txt`–`q3.txt`. `freeze-manifest-v2.json` закреплён до первого ответа. `frozen-v1` не исполнялся: v2 исключает старые evaluator notes. Исходная предметная история — TASK04 r3; её чистый технический rebase имеет r1–2. TASK04 r11 и будущие ответы в пакетах отсутствуют.

Наблюдаемый маршрут этой сессии: независимые no-history subagents. Он наследует Megafon AGENTS даже во временной папке, поэтому B′ является **ablation**, ordinary B — **NOT_RUN**. См. `context-probe.md`, `workspace-map-v2.json`. FRESH_HOST_SAVE_RELOAD этой работой не проверяется.

## Минимальная передача для обычного A/B

Используются текущий авторизованный Codex UI/host и существующая `.venv`; новых runtime/providers/ключей нет. Из корня репозитория:

```powershell
.\.venv\Scripts\python.exe -X utf8 evaluation/task05/handoff.py prepare --condition A --workspace "$env:TEMP\task05-ordinary-A-run02"
.\.venv\Scripts\python.exe -X utf8 evaluation/task05/handoff.py prepare --condition B --workspace "$env:TEMP\task05-ordinary-B-run02"
```

Папки должны быть новыми. Утилита отказывает при ancestry AGENTS. Для каждого условия открыть отдельный **новый чат** в его папке, без истории этой беседы/другого участника, с одинаковой выбранной моделью и настройками. Передать: «Прочитай request-q1.txt и RUNTIME.md как UTF-8 (`Get-Content -Encoding UTF8`) и выполни запрос; работай только в этой папке». Уточнение encoding одинаково для обоих: оно устраняет наблюдённый bootstrap mojibake; прежние prompts/ответы остаются неизменны, будущий run фиксирует это различие. Проверить и записать фактически унаследованные инструкции. Если B всё ещё получает Megafon procedures/правила/состояние родителя, ordinary B остаётся NOT_RUN; не удалять higher-priority instructions ради результата.

После сохранения обоих первых ответов выдать второй шаг:

```powershell
.\.venv\Scripts\python.exe -X utf8 evaluation/task05/handoff.py stage --condition A --phase q2 --workspace "$env:TEMP\task05-ordinary-A-run02"
.\.venv\Scripts\python.exe -X utf8 evaluation/task05/handoff.py stage --condition B --phase q2 --workspace "$env:TEMP\task05-ordinary-B-run02"
```

В тех же двух чатах: «Прочитай request-q2.txt и выполни запрос». Затем аналогично `--phase q3` и `request-q3.txt`. Собственная история и notes каждого сохраняются. До выдачи шага будущие inputs не помещать в рабочую папку. Код frozen-v2 намеренно соответствует первой измеренной версии; не подменять его исправленной реализацией без нового freeze. Новые прогоны сохранять отдельно.

Снимок ответа/состояния и хешей после каждого шага:

```powershell
.\.venv\Scripts\python.exe -X utf8 evaluation/task05/handoff.py snapshot --condition B --phase q1 --workspace "$env:TEMP\task05-ordinary-B-run02" --output evaluation/task05/new-run02/B/q1
```

Сохранить workspace с `logs` по завершении. `capture.py LOG_DIR UNIQUE_LABEL -- EXECUTABLE ARGS...` записывает точные command/cwd/stdout/stderr/exit/start/end/elapsed. Bootstrap и файловые операции вне capture перечисляются участником в meta; это ограничение полноты trace, не невидимая техническая изоляция. Протокол не требует конкретной последовательности tools. Никаких подсказок ответов от координатора.

## Оценка и исправления

`expectations-v1.json` и `rubric-v1.json` доступны только evaluator, не участникам. Оценивать полный первый ответ, источники и действительный результат сохранения отдельно. Два коротких сценария не показывают качество всего strategy workflow. Critical errors не компенсируются суммой баллов. Review автоматическое, не human validation.

Воспроизведение контрольных дефектов первой версии:

```powershell
.\.venv\Scripts\python.exe -X utf8 evaluation/task05/probe_controls.py --code-root evaluation/task05/frozen-v2/A --output evaluation/task05/new-controls-before.json
```

Для исправленной версии использовать `--code-root .` и другой новый output. Это deterministic correction check, не замена A/B первого прохода. Полная регрессия: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`.

Старые reports/входы/ответы не перезаписывать. Секреты не читать, материалы новым внешним сервисам не отправлять. Внешние действия, публикация, бизнес-эксперимент и глобальная конфигурация не входят в эту передачу.
