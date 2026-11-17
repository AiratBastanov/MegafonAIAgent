# Диагноз launcher и граница новой проверки TASK03

Проверка отдельного агента Codex `/root/fresh_launcher`, 16.11.2026. Это автоматический разбор кода и наблюдений, не новая сессия продуктового анализа и не человеческая приёмка. Каноническое состояние и исторические артефакты TASK02 не изменялись.

## Что действительно произошло раньше

Прочитаны `evaluation/run_fresh_host.py`, `fresh-session-audit.md`, `fresh-session-fixed/{launch,outcome,stop-observation}.json`, начало и конец `events.jsonl`, `stderr.txt`, outcomes двух более ранних попыток. В последнем запуске TASK02 новый процесс восстановил revision 2 и выполнил новый расчёт: завершённый `command_execution` item_26 содержит `ok=true`, 30 metric checks, 7 economic checks, расчёт размера групп и экономики. Последующий stdout содержит только ошибки переподключения; `stderr.txt` — idle timeout, request timed out и TLS unexpected EOF. Это подтверждает узкий recovery/next-step результат TASK02. Сохранение новой revision этим процессом не завершено.

Наблюдаемый дефект старого launcher: `last_activity` обновлялся при любом изменении размера stdout **или stderr**. Повторные status/reconnect сообщения поэтому откладывали таймаут без полезного шага. Они не означают восстановление сети. Сбой не даёт оснований менять провайдера, отключать sandbox или читать credentials. Ошибка OS 10013 в ранней попытке отличается от поздних transport failures после полезной работы.

Новая подготовительная задача `/root/fresh_launcher` также была прервана transport error и затем продолжена родителем. Это отдельное наблюдение делегирования, **не** результат новой fresh CLI проверки. Новая модель этим агентом не запускалась.

## Подтверждённый маршрут

Локально выполнены `codex --version`, `codex --help`, `codex exec --help`: установлен **codex-cli 0.169.0-alpha.11.1**. Executable найден через `Get-Command codex` в установленном расширении VS Code. `exec` поддерживает `--cd`, `--sandbox workspace-write`, `--skip-git-repo-check`, `--ephemeral`, `--json`, `--color never`, `--output-last-message`; plain exec не использует resume/fork. `--ephemeral` не означает отсутствия сохранения project files. Аргумент запроса и DEVNULL stdin исключают присоединение старого чата через stdin.

Применён [openai-docs SKILL.md](C:/Users/BastaPC/.codex/skills/.system/openai-docs/SKILL.md). Через web/open прочитано официальное [описание non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode), 16.11.2026, redirect с `https://developers.openai.com/codex/noninteractive`. Маршрут чтения — rendered summary хоста. Решение: использовать существующий exec и его JSONL events, без нового API/оркестратора. Фактические флаги сверены с установленной версией, а не перенесены из иной версии документации.

## Новый launcher

`evaluation/run_fresh_host_m2.py` запускает ровно **один** новый exec. Он записывает настоящий argv/request/PID/времена, исходные JSONL/stderr, вывод version/help, Python executable/version и версии всех pinned dependencies. Не читает конфигурацию/секреты и не меняет глобальные настройки. Новые папки результатов не перезаписываются; журнал находится вне чистого workspace. Перед запуском выполняется отдельный validated load. После завершения CLI выполняется ещё один отдельный load и сохраняется его stdout/exit code. Родитель не пишет продуктовый state за свежий процесс.

Путь Python задаётся обязательным `--python`; зависимости сверяются с `requirements.txt` чистой копии. Launcher prepend-ит его каталог в PATH дочернего процесса и передаёт `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8`, `MEGAFON_PROJECT_PYTHON`. Для воспроизводимости сам проект должен явно указывать этот interpreter или собственный setup. Windows `.venv` не копируется и не объявляется переносимой.

Технический timeout по умолчанию 600 секунд отсчитывается от успешно завершённого command/file/tool event. Сообщения агента, начатые операции, неуспешные команды и reconnect noise его не сбрасывают. Отдельно ограничены пять transport retries без завершённого действия; stderr и JSON counts не складываются как независимые повторения. OS 10013 завершает попытку сразу. Все пределы настраиваемы и защищают проверочный процесс от зависания, а не ограничивают продуктовые исследования. Длительная полезная операция без события завершения может потребовать большего явно заданного timeout: это ограничение наблюдения launcher, не доказательство отсутствия работы.

Остановка на Windows адресована только собственному PID из Popen и его дереву через `taskkill /PID ... /T /F`. Отказ в правах фиксируется как cleanup_failed; обхода нет. Артефакты остаются на диске. Принудительный технический stop не считается когерентным завершением агента. Даже exit 0, completed tool events и валидный load **сами по себе не дают PASS**: отдельный аудит должен открыть новый полезный артефакт, связанный новой revision, и проверить правильный next_action. Точные model identity/charges остаются неизвестными; usage сохраняется только если получен настоящий turn.completed.

Пример команды после подготовки чистого **незавершённого** checkpoint и файла обычного запроса:

```powershell
.\.venv\Scripts\python.exe evaluation/run_fresh_host_m2.py --workspace evaluation/task03/continuation-workspace --request evaluation/task03/continue-request.txt --output evaluation/task03/fresh-session-01 --python .venv/Scripts/python.exe --project-id demo-002 --timeout 600 --transport-retry-limit 5
```

Запрос: «Продолжи анализ проекта demo-002 по сохранённому состоянию». Полезная ограниченная фаза и обязанность сохранить revision должны следовать из файлов проекта; готовых ответов/поздних результатов в checkpoint быть не должно. Разрешённый запуск может требовать существующего host approval route для сети самого Codex; launcher не включает обходных флагов. При недоступности маршрута завершить независимую M2 работу и отметить точную проверку NOT_VERIFIED.

## Проверка кода

Focused tests в `tests/test_fresh_launcher.py` проверяют: reconnect/message не продлевают таймер; успешный tool сбрасывает retry window, failed command — нет; OS 10013 останавливает попытку; incremental JSONL сохраняет разделённые UTF-8 символы и последнюю строку без newline. Это детерминированные тесты guards, не имитация успешного fresh-host анализа. Фактический результат запуска тестов сообщает координатору отдельная tool-запись.

Предпусковое независимое ревью formats обнаружило ещё один дефект: timeout/OSError последующего loader мог прервать запись `outcome.json`. Исправлено: наблюдение о завершившемся CLI сохраняется **до** отдельного load, затем статус loader и диагностика записываются независимо. Focused test вводит обе ошибки и проверяет сохранность исходного CLI outcome; это не настоящая ошибка продуктового state и не результат fresh launch.
