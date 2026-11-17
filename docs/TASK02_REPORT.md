# TASK02 — реализованный M1 и наблюдаемая проверка

**TASK02_M1_VERIFIED — в определённой TASK02 границе.** Реализован агент для существующего Codex, выполнен фактический цикл на учебных входах, сохранены результаты и продолжение. Отдельный критерий свежей сессии пройден: новый процесс сам восстановил задачу и выполнил содержательный следующий шаг без повторного импорта. **Полный дополнительный CLI-цикл после этого шага не завершился из-за transport failures; новая state revision самим этим процессом не опубликована.** Это ограничение не скрывается за узким PASS.

Человеческое содержательное ревью, реальная экономическая информация и бизнес-решение ожидаются. Статус канонического проекта — `awaiting_decision`, не approved. Официальный дополнительный бриф не получен; учебный пример не является финальной демонстрацией по нему. Видео, публикация и M2–M6 не выполнялись.

## Что реализовано

| Файлы | Обязанность |
|---|---|
| [README](../README.md), [AGENTS](../AGENTS.md) | Один обычный запрос запускает/продолжает анализ; отдельные режимы разработки, нового продукта и resume; русский интерфейс |
| `knowledge/procedures/strategy-cycle.md`, `evidence-review.md` | Выбор следующего действия, исследование, варианты/стратегии, критика, остановка/коррекция |
| `knowledge/methods.md`, `record-contracts.md`, `tool-contracts.md` | Минимальная методика, provenance/claims/state и точные локальные контракты |
| `scripts/import_materials.py` | Простые DOCX с порядком/координатами, CSV/UTF-8, регистрация прочитанной web-выдержки; stable source ID и версии, reuse, ограничения |
| `scripts/analyze_table.py` | Явные суммы/отношения, единицы/периоды, missing/null, zero denominator, точное округление и fingerprints |
| `scripts/project_state.py` | validate/save/load/recover; current/previous/history, проверки ссылок/хешей/синтетики, исключение известного искусственного маркера |
| `tests/test_materials.py`, `tests/test_state.py` | 41 содержательный компонентный тест |
| `evaluation/make_inputs.py` | Только синтетические DOCX/CSV/spec/definitions, без стратегий и вымышленной трассы |
| `evaluation/check_arithmetic.py`, `calc_scenarios.py`, `verify_outputs.py` | Независимая арифметика, явные сценарии и структурная проверка ссылок пяти outputs |
| `evaluation/run_fresh_host.py` | Проверочный запуск нового существующего Codex CLI, точные argv/request/times/events; не новый агентный оркестратор |
| `projects/demo-001/` | Реальный анализ host LLM, версии входов, доказательства, расчёты, пять результатов v1/v2 и state |
| `docs/DEVELOPMENT_STATE.md` | Ход разработки отдельно от состояния продукта |

Runtime — стандартная библиотека Python. Новый LLM loop, LangGraph runtime, vector store, backend и hosted tracing не добавлены. Источник модели/tools — существующий Codex. Утилиты не выбирают победителя и не знают названия учебного продукта.

## Среда, setup и точные команды

Проверено: Windows, PowerShell5.1, Python3.12.10; `codex-cli 0.169.0-alpha.11.1`. Создана локальная `.venv`, сторонних runtime-пакетов нет, `requirements.txt` это явно фиксирует. Глобальные установки и настройки не менялись. Точная модель основного host/CLI не раскрыта в доступных записях; системная роль указывает семейство GPT-6, это не точный model ID.

```powershell
cd C:\Users\BastaPC\Desktop\MegafonAIAgent
python -m venv .venv
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/project_state.py load --project projects/demo-001
.\.venv\Scripts\python.exe scripts/project_state.py validate --project projects/demo-001
.\.venv\Scripts\python.exe evaluation/verify_outputs.py --project projects/demo-001 --version v2 --output evaluation/output-references-final.json
```

Обычная эксплуатация — открыть папку в разрешённом Codex и написать: **«Продолжи анализ проекта demo-001 по сохранённому состоянию»**. Человек не запускает каждую команду. Для нового проекта дать ID, решение и путь разрешённых входов; образцы в README.

Воспроизведение входов/арифметики в отдельном новом ID:

```powershell
.\.venv\Scripts\python.exe evaluation/make_inputs.py --project projects/repro-001
.\.venv\Scripts\python.exe scripts/import_materials.py --project projects/repro-001 --source-id S001 --input inputs/brief-v1.docx --kind docx --synthetic
.\.venv\Scripts\python.exe scripts/import_materials.py --project projects/repro-001 --source-id S002 --input inputs/cohorts-v1.csv --kind csv --synthetic
.\.venv\Scripts\python.exe scripts/analyze_table.py --project projects/repro-001 --input inputs/cohorts-v1.csv --spec inputs/metrics-total.json --source-id S002 --source-version 1 --output evidence/calculations/total-v1.json
.\.venv\Scripts\python.exe evaluation/check_arithmetic.py --input projects/repro-001/inputs/cohorts-v1.csv --result projects/repro-001/evidence/calculations/total-v1.json --output projects/repro-001/evidence/calculations/check-total-v1.json
```

Для проверки нового чата существующий зафиксированный пакет распаковать в новую разрешённую папку и открыть её новым чатом, без resume/fork. Точный запуск наблюдаемого успешного восстановления:

```powershell
.\.venv\Scripts\python.exe evaluation/run_fresh_host.py --workspace evaluation/continuation-workspace-v2 --request evaluation/continue-request.txt --output evaluation/fresh-session-fixed --timeout 600
```

Он уже выполнен: существующие output folders не перезаписываются, при новом воспроизведении нужен новый путь output. Внутри запускался `codex exec --cd <isolated-copy> --sandbox workspace-write --skip-git-repo-check --ephemeral --json --color never --output-last-message <file> "Продолжи анализ проекта demo-001 по сохранённому состоянию."`. Перед запуском прочитаны локальные `--help` и [официальный non-interactive guide](https://learn.chatgpt.com/docs/non-interactive-mode). `resume --last`, fork, API keys и обход sandbox не применялись. Поддерживаемый host approval route разрешил сеть существующего Codex; разрешения дочерних команд оставались workspace-write. В другом managed profile этот маршрут может быть недоступен.

## Наблюдаемые результаты — раздельно

| Проверка | Результат и свидетельство | Практическая граница |
|---|---|---|
| Структура/детерминированная корректность | **PASS:41/41**, `evaluation/structural-tests.txt/.json`; 21 materials +20 state. Последний набор 0,884 с, wrapper1,063 с | Не доказывает качество решения LLM |
| DOCX/CSV | Порядок paragraph/table/cell, точные locators, weighted arithmetic, units/periods, missing и 0 знаменатель, invalid input, zip guard | Сложный DOCX явно отклоняется; PDF/XLSX не заявлены |
| Сохранение/повреждение | Тесты failed os.replace, invalid draft, corrupt JSON/checksum/artifact, missing reference, previous/history/explicit recovery; symlink test без skip | Инъекция сбоя компонента, не полная crash matrix/аварийная UI-отмена; одного писателя обеспечивает дисциплина, lock нет |
| Настоящий цикл host LLM | **PASS**: DOCX/CSV/web реально прочитаны, вопросы/гипотезы пересмотрены,4 альтернативы,5 результатов, сценарная экономика, независимая арифметика | Учебный набор, не реальный рыночный эффект; [наблюдение](../projects/demo-001/evidence/run-observation.md) |
| Stop/checkpoint | **PASS**: research revision1 в 09:54:42 МСК до синтеза; revision2 до синтеза после исправления CLI; ZIP и capture inventories сохранены | Запланированный кооперативный стоп, не имитация нажатия аварийной отмены |
| Коррекция | **PASS**: S004 — маркированный тест. S002@2 меняет только retained_d28 recurring60→40; агрегат 28→24%. Изменена рекомендация: сначала сверка учёта, затем условный пилот | Не вымышленное решение/исправление настоящего владельца. [Влияние](../projects/demo-001/evidence/correction-impact-v2.md) |
| Источники→claims→выдача | **PASS**: current содержит 14 claims/45 pinned artifacts;5 outputs структурно проверены; точные координаты/смысл сверены отдельным review | Валидатор ссылок не удостоверяет истинность/полномочия человека |
| Содержательное ревью | **PASS после исправлений**: [v1](../evaluation/review-v1.md), [v2](../evaluation/review-v2.md); актуальное evidence/review-v2 привязано state | Реальные отдельные подагенты и координатор, не человеческие эксперты |
| Вредоносный источник | **PASS в узком примере**: no-history подагент прочитал источник, игнорировал embedded commands, не объявил отсутствующую функцию. Маркер отсутствует в 11 проверенных outputs; `evaluation/safety/` | Отсутствие чтения private fixture/сетевых вызовов отражено отчётом подагента; полный его низкоуровневый tool log не экспортирован. Это не универсальная защита от prompt injection |
| Чтение веба | **PASS**: реальный web/open официальной справки Todoist; S003@1 хранит дату, URL/redirect, координату и разрешённую короткую выдержку | Host-rendered rewritten summary, не исходный HTML; origin server/cache отдельно не проверены. Сниппет не использован вместо страницы |
| Fresh-session recovery/next step | **PASS точного критерия TASK02**: новый процесс восстановил revision2, прочитал инструкции, сохранил новый sample-size/per-treated economics calculation без повторного ingestion | Полный дополнительный CLI-цикл и новая state publication после этого шага **не завершены**; подробности ниже |
| Внешние/человеческие проверки | **PENDING**: официальный extra brief, human review, business approval, final media/access/submission | Не подменяются авто-тестами и не входят в завершённый M1 |

## Свежая сессия: факты, а не same-chat reread

`evaluation/checkpoint-capture-v2.json` и `checkpoint-before-synthesis-v2.zip` фиксируют 41 файл, доступный в 07:12:32 UTC. Там нет outputs, поздней коррекции или evaluation answers. Канонические outputs/v1 появились позже. Начальный запрос содержал только project ID и просьбу продолжить; cwd передан флагом. Новый thread ID записан CLI; прежняя беседа не передавалась.

`evaluation/fresh-session-fixed/events.jsonl`: успешный load revision2, восстановленная objective/unfinished, новый вопрос о размере теста и пороге оплаты, запись script/spec и успешный запуск нового расчёта. В 07:16:50 UTC сохранён [continuation-check-v1.json](../evaluation/continuation-workspace-v2/projects/demo-001/evidence/calculations/continuation-check-v1.json): новая оценка выборки и экономика для 100/50/356 получателей воздействия. Это работа над незавершённым планом проверки, а не только чтение файла. Импорт не запускался; все 41 исходных файлов остались неизменны. Арифметическая перепроверка готовых значений **была**, заявлять отсутствие любого повторного труда нельзя.

После этого шли TLS/timeout reconnect failures без нового полезного результата. Координатор остановил только собственный проверочный процесс в 10:32:32 МСК; сохранённые новые артефакты и канонический проект целы. `turn.completed`/usage отсутствуют. Нет утверждения, что весь дополнительный прогон завершился или что свежий агент сохранил новую state revision. [Независимый аудит](../evaluation/fresh-session-audit.md) подтверждает ровно требуемый recovery/next-step PASS; `stop-observation.json` поясняет ненулевой exit.

Предыдущие попытки сохранены, не скрыты: первая — OS10013 network denial,0 model commands; вторая через разрешённый маршрут —3 команды, сбой UTF-8 вывода state и ограничитель 300 с. После исправления была создана **новая фактическая незавершённая** revision2 до синтеза, а не искусственный rollback после готовых стратегий. Проверочный launcher изменён на timeout отсутствия вывода; исследовательской квоты нет. Повторять тот же сломанный сетевой маршрут бесконечно не стали.

## Найденные дефекты и исправления

- Windows cp1251 не выводил стрелку в JSON состояния: CLI stdout/stderr переключены на UTF-8; регрессия проверена через subprocess с cp1251.
- DOCX терял `noBreakHyphen` и не отклонял tracked moves: символ сохраняется, move elements явно отвергаются. Метод извлечения получил новую версию.
- Большие числа могли округляться раньше финального шага: введена явная числовая safeguard и точное суммирование/рациональное ROUND_HALF_UP.
- Чтение старого source metadata через symlink могло выйти за проект: paths проверяются до чтения.
- Несвязанный artifact мог ссылаться на чужой source: проверяется membership либо документированное происхождение calculation с source/version/input hash.
- Recovery копировал сырые повреждённые bytes: теперь сохраняется только безопасная диагностическая сводка hash/size/reason, искусственный маркер не копируется.
- Ревью стратегий исправило неоднозначный контроль эксперимента,28-дневное окно вместо полного окна оплаты, координаты JSON claims и необоснованную подмену выручки вкладом. Новое описание сравнивает пакет помощи с текущим продуктом, отдельно определяет 30 суток оплаты/затрат и относит экономический порог к числу получателей воздействия.

Во время подготовки встречались неверная кодировка консольного чтения, несошедшиеся контексты apply_patch, чтение ещё не созданного review-файла и отказ process inspection/stop в обычном sandbox. Они не изменили входные данные; маршруты исправлены/прекращены. Автоматический approval review не отклонял авторизованные запуски/остановку; права хоста не отключались.

## Источники, ограничения и зависимости доставки

Поправки плана и выбранные принципы записаны в существующих [PROJECT_PLAN](PROJECT_PLAN.md), [ARCHITECTURE](ARCHITECTURE.md), [RESEARCH_SOURCES](RESEARCH_SOURCES.md). Прочитаны указанные LangChain repo/overview, Anthropic engineering guidance и LangGraph persistence. Приняты простые tool contracts, выбор процедур, проверка результатов и файловое продолжение. Framework не даёт автоматическую память чужому Codex-чату; M1 не требует его зависимости. Шесть названных пользовательских руководств отсутствовали среди файлов проекта/приложенного контекста; их локальное чтение не заявляется, явные принципы TASK02 применены.

Повторная проверка [страницы организатора](https://challenge.mgimo.ai/)16.11 подтвердила дедлайн **22.11.2026,23:59 Europe/Moscow**. [Кабинет кейса](https://challenge.mgimo.ai/cabinet/nominations/ai-project) недоступен текущему web route; это не свидетельство отсутствия/непубликации extra brief. Пароли не запрашивались. До M6 нужны доступный бриф или подтверждение допустимости альтернативы, реальное человеческое ревью, полномочия/доступ капитана и жюри, запись видео/отчёт и отдельная авторизация публикации. Часы/состав команды неизвестны;10–16 человеко-часов TASK01 не были таймером.

Текущий профиль повторно обозначает `.agents` read-only. Поэтому используются обычные procedure files; actual fresh process прочитал AGENTS и обе процедуры. Автообнаружение repository-local skills не заявляется. Локальный Git checkout отсутствует; intended remote сохранён, init/push/visibility не выполнялись. Исходный brief SHA-256 совпал с TASK01: `C0DC6437E6489AC54BC13DF40BEE6CF8A726D19C06E309EEF5CC56E9BC779BD3`.

Технические limits:20MiB/file,80MiB unpacked DOCX,50000CSV rows; настраиваемые `--max-*` и numeric guard18 цифр/|exponent|≤12. Это не квоты исследования и не испытанная предельная производительность. Нет concurrency locks, полной crash matrix, фонового мониторинга, XLSX/PDF/OCR и проверки на втором хосте. Пять outputs — условное предложение, не факты о рынке или действующих возможностях настоящего МегаФона.

## Ресурсы

Машинные интервалы/счётчики: [resource-accounting.json](../evaluation/resource-accounting.json). Разработка началась 09:32:05 МСК 16.11; техническая фиксация завершения — 10:56:29, elapsed **5064,292 с (84 мин 24,292 с)**. Демонстрационный интервал от сохранённого факта чтения публичной страницы 09:43:51 до reviewed state revision5 в 10:34:59 — **3068,568 с (51 мин 08,568 с)**. Он включает перемежающуюся разработку/проверки и ожидания: эти интервалы **нельзя складывать** как независимые трудозатраты.

Три новых CLI-процесса заняли 300,047 с/300,015 с/1195,828 с; это подмножество общего elapsed. В последнем emitted log23 завершённых command executions,1 из них с ошибкой (поиск отсутствовавшей evaluation в чистой копии),5 сообщений sampling retry. Первый процесс:5 sampling retry и 8 HTTP wait retry; второй:1 ошибочная из 3 команд. Полные event counters доступны в JSON; корневой полный tool/token счётчик и скрытая активность недоступны. Значимые действия проекта записаны отдельно, без рекурсивного logging.

Делегирование было реальным: materials/state реализовали разные модули и взаимно проверили код; plan_amendments обновил план, затем провёл два содержательных review; source_review без истории выполнил проверку источника. Общий state писал только координатор. Tokens, точный model ID, денежные списания и ненаблюдаемое время человека — `unknown/null`. Новых платных провайдеров/покупок не было; это **не нулевая полная стоимость**. Во время работы новых содержательных сообщений пользователя не наблюдалось; коррекция синтетическая, human review/approval не имитировались.

## Где смотреть и что дальше

Актуальный комплект: [situation](../projects/demo-001/outputs/v2/situation.md), [options](../projects/demo-001/outputs/v2/options.md), [product strategy](../projects/demo-001/outputs/v2/product-strategy.md), [communication strategy](../projects/demo-001/outputs/v2/communication-strategy.md), [validation plan](../projects/demo-001/outputs/v2/validation-plan.md). Состояние: `projects/demo-001/state/current.json` revision5; previous revision4; обе research interruption revisions и outputs/v1 сохранены.

Следующая ограниченная задача — получить доступный официальный extra brief и выполнить gap-анализ учебного пакета к нему; если меняются входы, провести тот же цикл на новом project ID. До этого владелец может проверить v2; реальные расходы/пилот/закрытие остаются ожидающими решения. Расширение форматов M2 и финальная публикация не являются скрытой частью TASK02.
