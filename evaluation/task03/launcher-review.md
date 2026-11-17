# Предпусковое независимое review launcher M2

Дата: 16.11.2026. Проверяющий: отдельный подагент `formats`, не автор launcher. Проверены `evaluation/run_fresh_host_m2.py` и `tests/test_fresh_launcher.py`; модель не запускалась, состояние проектов не менялось. Это автоматическое code review, не наблюдение fresh session и не human approval.

## Результат

**Можно выполнить один проверочный запуск после подготовки чистого checkpoint.** Блокирующих нарушений маршрута новой сессии, подмены provider или обхода разрешений в проверенном коде не найдено. Четыре focused tests PASS; они проверяют guards, а не доказывают выполнение нового процесса.

- `main()` проверяет фактические `codex --version`, `codex --help`, `codex exec --help`, затем вызывает один `exec --ephemeral --sandbox workspace-write --skip-git-repo-check --json`. В argv нет `resume`, `fork`, модельных/provider overrides, отключения ограничений. Stdin закрыт; в запрос передаётся отдельный обычный текст, прежний transcript не добавляется.
- `environment()` вызывает конкретный `--python`, записывает `sys.executable`, Python version и версии каждого pin из requirements; несовпадение останавливает запуск. В env дочернего процесса только добавляются UTF-8, путь выбранного интерпретатора и PATH. `.venv` не копируется. Фактическое использование этого Python агентом всё равно следует проверить по событиям.
- `Progress` не продлевает таймер на agent_message/reconnect и не суммирует stderr/JSON как независимые retries. Только успешно завершённое tool/command действие сбрасывает окно; это технический прогресс, его содержательность отдельно проверяется по артефактам. Неудачные команды не сбрасывают окно.
- `stop_owned()` работает только с PID созданного Popen; Windows taskkill адресует его дерево, без поиска чужих процессов и обхода запрета. При невозможности завершения выставляется cleanup_failed. Запуск скрыт через CREATE_NO_WINDOW.
- Starting load и subsequent load используют отдельные `subprocess.run` с выбранным Python. После модели parent не записывает state; последующий load запускается только если процесс уже завершён. Логи находятся вне чистого workspace.
- Exit0 launcher означает exit0 CLI и loader. Это **не** доказательство новой revision: код прямо сохраняет `substantive_continuation_status=requires_independent_artifact_and_state_audit`. Для stronger TASK03 нужны отдельные diff/claims/artifact/state проверки и подтверждение того, что revision опубликовал новый процесс.

## Замечание L01 — сохранить диагностику, если subsequent load сам завершился исключением

Серьёзность: умеренная, не препятствует авторизованному запуску. Основание: `load_state()` использует `run_capture(...timeout=30)`; вызов после завершения CLI находится до записи outcome.json. Если loader выдаёт TimeoutExpired/OSError, outer exception handler только печатает ошибку, поэтому уже известные argv/elapsed/CLI outcome остаются разнесёнными по launch/events и итоговый outcome.json не появляется.

Рекомендация автору: перехватить исключение вокруг subsequent load, сохранить `subsequent_load_exit_code=null`, отдельный тип ошибки и status; затем всё равно записать outcome.json и вернуть ненулевой exit. Аналогично полезно не терять stderr/taskkill returncode при timeout cleanup. Это улучшение достоверности диагностики, не повод объявлять fresh execution пройденной или повторять модель без сверки сохранённых результатов.

## Проверка

Команда: `.\.venv\Scripts\python.exe -m unittest tests.test_fresh_launcher -v`.

Все четыре теста PASS: reconnect/status не поддерживают процесс, successful action сбрасывает retry window, permission denial останавливает сразу, UTF-8/partial JSON lines не теряются. Не выполнялись модельный запуск, stop реального процесса или сильная приёмка сохранения/reload.
