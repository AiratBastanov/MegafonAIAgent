# TASK03 — M2: форматы, второй продуктовый выбор и продолжение

**TASK03_M2_IMPLEMENTED_WITH_VERIFICATION_GAPS**,16 ноября 2026. Ограниченные XLSX/PDF, второй содержательный анализ, коррекция и каноническое сохранение реализованы и проверены. Сильная проверка нового процесса «полезная фаза → новая revision → отдельный load» остаётся **NOT_VERIFIED**: Codex восстановил checkpoint, но транспорт оборвался до нового расчёта/state. Это конкретный пробел исполнения, а не незавершённая реализация форматов.

Результат: **demo-002, revision4, outputs/v2, awaiting_decision**;56 закреплённых артефактов,14 claims,6 версий источников. [Полный пакет для ревью](TASK03_REVIEW_PACKET.md) содержит все пять документов, исходные координаты и расчёты; это производное представление, не новый первичный источник. [Проект](../projects/demo-002/README.md), [state](../projects/demo-002/state/current.json), [рабочая запись](TASK03_WORKLOG.md).

| Граница результата | Фактический статус |
|---|---|
| Реализация поддерживаемых XLSX/PDF и provenance | Проверена на объявленном ниже подмножестве |
| Детерминированные проверки | 62 теста PASS,0 ошибок/падений/пропусков; source/arithmetic/state проверки отдельно |
| Реальный анализ координатором Codex | Выполнен: вопросы, сайт, конфликт, расчёты, пять стратегий, коррекция, review и save |
| Новый процесс восстановил unfinished checkpoint | Наблюдалось на demo-002 revision1 |
| Новый процесс выполнил фазу и сохранил новую revision, найденную после load | **NOT_VERIFIED**, TLS/reset/HTTP403; существующая revision1 сохранна |
| Независимый автоматический обзор | Код и пять v2 документов проверены; существенные замечания исправлены |
| Человеческая проверка/решение бизнеса | Не получены, `awaiting_decision`; автоматическое review их не заменяет |
| Официальный дополнительный бриф | Pending: кабинет недоступен текущему web route; публикация брифа неизвестна |
| Видео, публикация, конкурсная готовность, улучшение относительно baseline | Не выполнялись/не заявляются |

## Реализация и границы

Сохранены один Codex-координатор, явные процедуры и детерминированные Python utilities. Общую память каждого проекта пишет только координатор; подагенты реализовали/проверили независимые части. Нет нового приложения, автономного цикла, LangGraph runtime, базы или inference API. Repository skills в read-only `.agents` не устанавливались; применяются обычные procedures. AGENTS остаётся кратким.

Проектная `.venv`: Python **3.12.10**, `openpyxl==3.1.5`, `pypdf==7.1.0`, `et-xmlfile==2.0.0` ([requirements](../requirements.txt)). Официальные tutorial/metadata и локальная совместимость проверены, `pip check` успешен. Зависимости не подменены глобальными. Setup описан в README; Windows venv не копируется между рабочими копиями. Явный interpreter свежего запуска — `C:\Users\BastaPC\Desktop\MegafonAIAgent\.venv\Scripts\python.exe`; actual versions и hash requirements сохранены в [environment](../evaluation/task03/fresh-session-01/environment.json).

[import_materials.py](../scripts/import_materials.py) и [extract_formats.py](../scripts/extract_formats.py) добавляют:

- **XLSX:** обязательный выбор конечных диапазонов; исходные имена листов/адреса, значения и типы, number format, даты, единицы/периоды selection и пропуски. Сохраняются inventory листов, hidden/merged structures. Merged anchor не размножается. Формула отделена от cache (`missing/error/present`, freshness=`unknown`), `data_only` не назван пересчётом. Макросы, external links, embedded objects и выбранные array/data-table formulas отклоняются. Ссылки/команды из данных не исполняются; содержание картинок/диаграмм не извлекается, ограничение записано. Единицы — явное определение по словарю, не вывод из number format.
- **PDF:** простой нешифрованный неразвёрнутый текстовый слой, physical page и `block` locator, hash текста; page label отдельно. Пустые страницы, шифрование, неподдерживаемые формы/поворот или некачественное извлечение дают объяснимый отказ без успешного пустого source. Признаки сложного расположения/аннотаций/XObject дают `needs_layout_review` и наследуемые limitations: до решающего использования нужна проверка/иной экспорт. OCR, визуальная приёмка и произвольные PDF-таблицы не заявлены.

[analyze_table.py](../scripts/analyze_table.py) сохраняет CSV и принимает зарегистрированную XLSX-версию. Spec связывает нормализованные поля с ячейками; `input.sha256` остаётся original XLSX hash, provenance несёт extract hash, метод, ограничения и координаты. Числовой путь использует только literal cells: формула даже с числовым cache, ошибка, merged, дата/boolean в числовом поле отклоняются. Hidden требует явного include_hidden; единицы и периоды **всех** mapped cells проверяются. Пропуск остаётся null. Нет eval/движка пересчёта Excel.

Source/claim/state contracts версии1 сохранены без миграции. Импорт не равен проверке всех claims. Synthetic наследуется расчётами, интерпретация остаётся интерпретацией. Старые DOCX/CSV/web и все demo-001 revisions загружаются. `project_state.py` не менялся; ARCHITECTURE приведён в соответствие коду: explicit recover сохраняет hash/size/reason с `raw_preserved=false`, а не raw corrupt copy. Исторические отчёты не переписаны.

Настраиваемые safeguards:20MiB/вход,80MiB распакованного OOXML,50 000 CSV rows,100 000 XLSX cells с потенциальным merge expansion,64 sheets; PDF200 pages,8MiB decoded stream/page,2млн символов. PDF декодируется до проверки длины: абсолютная защита памяти от враждебных файлов не заявлена. Предельная производительность/полная crash matrix не испытаны. [Tool contracts](../knowledge/tool-contracts.md) описывают поддержанный маршрут и отказы. Эти границы не являются квотой исследования.

## M1 и историческое продолжение

Прочитаны actual code/tests/state, все пять действующих outputs/v2 demo-001 и решающие исходники. [Независимое M1 review](../evaluation/task03/m1-content-review.md):45 pinned artifacts,30 показателей сверены из raw CSV через Fraction,7 сценариев проверены отдельно. Существенных новых стратегических дефектов нет: знаменатель пилота —100 получателей воздействия, обещания ограничены возможностями, варианты различаются, окна и причинные ограничения указаны. Малое сокращение старого C007 не приводит к ошибке в действующих outputs; новая версия без содержательной причины не создавалась.

Канонический demo-001 остался **revision5/outputs v2/awaiting_decision**,64 файла совпадают с исходным manifest. Его статус не блокировал разработку. [Финальная проверка](../evaluation/task03/correction-final.json) также валидирует demo-002 revisions1–4.

[Interrupted calculation TASK02](../evaluation/task03/historical-continuation-review.md) проверен в собственной pre-correction revision2:7 refs и41 checkpoint files совпали. Новый расчёт без reimport действительно полезен и применим в той ветке, но остался вне опубликованного state. Зависимость от прежнего p0=60% superseded для canonical p0=40%: прежний ориентир356/arm при соответствующем пересчёте становится388/arm. Неизменённые формулы/расходы требуют applicability check; артефакт не удалён и не перенесён молча в canonical.

TASK02 сохраняет исходную узкую приёмку recovery+substantive next step PASS; последующий полный CLI-цикл/new state не завершились. TASK03 требует более сильного наблюдения, его нельзя получить задним числом из TASK02.

## Второй выбор и доказательства

[Запрос руководителя](../projects/demo-002/project.md): выбрать аудиторию и предложение B2B-передачи файлов. Это иной выбор, чем исправление удержания. Пример явно учебный, поскольку [официальный кабинет](https://challenge.mgimo.ai/cabinet/nominations/ai-project) вернул `not accessible via this tool`; из этого не выводилось отсутствие публикации. Реальных интервью, клиентов или закрытых данных здесь нет.

Fixture utility создаёт только PDF/XLSX: победитель и стратегии не зашиты. Агент выбрал decision-changing вопросы до synthesis: значение оплаты, соответствие функции задаче, альтернативы, чувствительность затрат. Сохранены вопросы, actual imports/checks, расчёты и последовательные states. [Наблюдение действий](../projects/demo-002/evidence/run-observation-v2.md) и [журнал](../projects/demo-002/evidence/actions-snapshot-v1.jsonl) не являются скрытой трассой рассуждений; журнал честно помечен ретроспективным по действительным logs/timestamps.

| Основание | Locator и значение для выбора |
|---|---|
| Возможности | S001@1 physical-page1/block4–8: исходящая ссылка, ручной отзыв,2GB/file,7days; нет входящей загрузки/пароля/SSO/audit. Production приёмка не проводилась |
| «8 paid pilots» против учёта | S001@1 physical-page2/block2–4 различает interest и проверенную оплату; S002@1 `'Воронка'!E3:F4`: interest5/8, paid302/1. C002 superseded, C006 объясняет конфликт |
| Знаменатели | S002@1 `'Воронка'!C3:F4`, C007/funnel-v1: paid/trial2/8=25% и1/10=10%; paid/contacted2/20=10% и1/20=5%. Малые синтетические группы не доказывают эффект аудитории |
| Реальная исходящая альтернатива | S003@1, [Dropbox Transfer](https://help.dropbox.com/share/dropbox-transfer), host lines55–58/70–85: получатель без аккаунта, Basic2GB/transfer и7days. Предел transfer не равен file. Нельзя обещать уникальность функции |
| Реальная входящая альтернатива | S004@1, [Dropbox file requests](https://help.dropbox.com/share/create-file-request), lines55–63/82: входящий сбор без аккаунта, возможное admin ограничение. Своя разработка для бухбюро требует отдельной ценности |
| Расходы | S002@1→2 `'Экономика'!E3`, S005@1 line1–5: только синтетическое допущение30→90min поддержки; C009 superseded C013, не новое рыночное измерение |

Public pages реально прочитаны16.11 через host web/open, сохранены URL, дата, excerpt/locator. Это rendered excerpt, не raw HTML; origin/cache freshness неизвестна. Видимые даты обновления24.09.2026/15.05.2025 не являются временем нашего чтения. Sources ограничивают обещание/выбор, но не доказывают спрос, качество или региональную доступность. Применённые первичные документы и решения — [RESEARCH_SOURCES](RESEARCH_SOURCES.md#task03-references).

Все20 PDF фрагментов сверены с manifest и literal source bytes собственного simple-text fixture, physical pages1/2 и labels A/1 различаются.19 решающих numeric cells проверены с raw OOXML —39 fidelity checks каждой версии. Это узкая доказанная полнота своего образца, не визуальный аудит или гарантия чужого PDF. Synthetic lineage сохранена.

Пять outputs/v2 полны и согласованы. Четыре варианта: внутренний прототип без коммерческого запуска; ограниченный тест исходящего предложения агентствам с ручной помощью; инвестиция во входящий сбор для бухбюро; закрытие самостоятельного направления. Status quo имеет цену ожидания; close требует проверки обязательств/неизвестной стоимости выхода. Предлагается лишь первый тест при бюджете владельца: нынешняя функция соответствует исходящей задаче и требует меньше разработки, но сегмент не доказан. До решения сохраняется прототип.

Коммуникация предлагает проверить полезность передачи/сопровождения, не «уникальный безопасный файлообмен» и не измеренную экономию. Current/planned/unproven разделены, отзыв ссылки не возвращает скачанную копию. Продукт и сообщение относятся к одному пакету/аудитории. Дополнительная ценность ручной координации против обычного инструмента остаётся гипотезой.

Price3000,infra600,support rate600RUB/hour,fixed30000,setup60000 — синтетические допущения. До коррекции margin2100, покрытие fixed с15, при20 остаток12000/условный payback5 месяцев. После30→90min: **margin1500;20 дают ровно0, положительный остаток с21; конечного возврата setup при20 нет**. При180min/N20 остаток−18000. CAC/налоги/неоплатившие пробы/продления неизвестны: остаток до них не является фактической прибылью. Независимая Fraction/OOXML проверка сверила6 конверсий и10 сценариев каждой версии.

Новый source/result не перезаписал прежние версии. Воронка не изменилась, поэтому funnel-v1/C007 переиспользован с S002@1 и applicability explanation. Обновлены затронутые экономика/C009→C013 и риск. Рекомендация теста не перевёрнута искусственно; масштабирование не обосновано. История:revision1 checkpoint,revision2/v1,revision3/v2,revision4/review. Финальный next_action — владелец/реальные данные, не reimport/автоматический пилот.

## Ревью и проверки

[Code review](../evaluation/task03/code-review-v1.md) воспроизвело три материальных дефекта: mixed periods разных ranges; неучтённая merged allocation до bound; пропуск cell count в UTF-16 XML. Все исправлены с focused tests. [Launcher review](../evaluation/task03/launcher-review.md): потеря outcome при исключении subsequent loader исправлена сохранением диагностики до loader и при Timeout/OSError. Это отдельные автоматические рецензенты, не human approval.

[Strategy review v1](../evaluation/task03/demo002-review-v1.md) выявил несовместимые окна и смешение trials/полного paid month. [Повторный v2](../evaluation/task03/demo002-review-v2.md) подтвердил исправления: day0 общий оффер,day23 последний send,day30 зрелый исход; paid-month/renewal имеют отдельный follow-up. Затраты всех10 организаций, включая неоплативших, учтены; расход на плательщика при нуле оплат неопределён, пересекающиеся представления не складываются. Прагматический gate7/10 организаций с сокращением медианы активного времени минимум5min не назван статистическим доказательством рынка. Указаны comparator, назначение порядка, metric definitions, окна, thresholds и stops при вреде. R3/C003 закрыто финальным state-only save, outputs/v2 неизменны. [Финальная дельта review](../evaluation/task03/final-state-review.md): PASS, все56 hashes, пять полных текстов в packet/revision4.

| Фактическая команда/проверка | Результат |
|---|---|
| `.venv\Scripts\python.exe -m pip check` | PASS; pins совпали с interpreter metadata |
| `evaluation/run_unit_checks.py --output evaluation/task03/checks-initial` |55 PASS,1.703s после первой реализации |
| `evaluation/run_unit_checks.py --output evaluation/task03/checks-final` |**62 PASS**,0skip,1.657s: [JSON](../evaluation/task03/checks-final/result.json), [полный log](../evaluation/task03/checks-final/tests.txt) |
| `evaluation/check_m2_fidelity.py --project projects/demo-002 --version 1/2 --output evidence/fidelity-v1/v2.json` |Два отдельных запуска, по39 проверок; [v2](../projects/demo-002/evidence/fidelity-v2.json), visual_layout_verified=false |
| `evaluation/check_offer_arithmetic.py --project projects/demo-002 --version 1/2 --output evidence/calculations/independent-v1/v2.json` |Два запуска, по16 сравнений; [v2](../projects/demo-002/evidence/calculations/independent-v2.json) |
| `evaluation/check_correction_m2.py --output evaluation/task03/correction-final.json` |Ровно E3; history1–4 валидна; demo-00164/64 неизменны |
| `scripts/project_state.py save --project projects/demo-002 --draft drafts/final-v2.json`, затем отдельный process `load --project projects/demo-002` |Revision4,56 artifacts,warnings=[]; [save](../evaluation/task03/demo-final-save.json), [load](../evaluation/task03/demo-final-load.json). Canonical/root save, не fresh-host доказательство |
| `evaluation/make_review_packet.py --project projects/demo-002 --version v2 --output docs/TASK03_REVIEW_PACKET.md` |Hashes/current refs проверены, полные5 текстов и основания; snapshot не перезаписывается |

Utilities запускались проектным `.venv\Scripts\python.exe -X utf8`; `1/2` в таблице означает два запуска, не синтаксис CLI. Повторные вычисления требуют новых output paths/проверочной копии. Полный набор: исходные41 и21 новый тест (11 format,5 XLSX-calculation,5 launcher). Проверены coordinates/types/cache/hidden/merged/missing/units/periods, PDF pages/text/unsupported, арифметика, hashes/versions/synthetic/state. После полного набора код не менялся, финальные document/state проверки выполнены отдельно.

Фактически выполненный расчёт коррекции (повторять в копии или с новым output):

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/analyze_table.py --project projects/demo-002 --input inputs/offer-v2.xlsx --spec inputs/metrics-economics-v1.json --source-id S002 --source-version 2 --output evidence/calculations/economics-raw-v2.json
.\.venv\Scripts\python.exe -X utf8 evaluation/calc_offer_scenarios.py --project projects/demo-002 --raw-metrics evidence/calculations/economics-raw-v2.json --assumptions inputs/economics-sensitivity-v1.json --output evidence/calculations/economics-v2.json
```

## Реальный fresh-host запуск и пробел

Старые launcher/logs изучены до retry: статус/reconnect продлевал наблюдение без полезной работы, TASK02 также имел отдельные OS10013/transport проблемы. Новый launcher отличает завершённые команды от шума, создаёт один процесс, сохраняет диагностику и технически ограничивает бесполезные переподключения. Это не бюджет исследования.

Unfinished revision1 сохранён09:37:07 UTC; [capture](../evaluation/task03/checkpoint-capture.json)09:38:06:39 файлов, [архив](../evaluation/task03/checkpoint-before-conflict.zip), [чистая копия](../evaluation/task03/continuation-workspace/AGENTS.md). Нет поздних outputs/correction/evaluator answers/venv. RUNTIME.md задаёт явный interpreter. Канонический проект позже развивался отдельно.

CLI0.169.0-alpha.11.1: прочитаны actual `--help`/`exec --help` и первичная non-interactive документация. Один новый `exec --ephemeral --sandbox workspace-write --skip-git-repo-check --json --color never --output-last-message`, без resume/fork/transcript/provider override/копирования auth. Host escalation для запуска одобрен, отказ auto-review не заявляется. Обычный запрос: «Продолжи анализ проекта demo-002 по сохранённому состоянию.»

```powershell
.\.venv\Scripts\python.exe -X utf8 evaluation/run_fresh_host_m2.py --workspace evaluation/task03/continuation-workspace --request evaluation/task03/continue-request.txt --output evaluation/task03/fresh-session-01 --python .venv/Scripts/python.exe --project-id demo-002 --timeout 600 --transport-retry-limit 5
```

[Events](../evaluation/task03/fresh-session-01/events.jsonl): thread `01a1e3b8-ebf4-7c71-b4c4-3c0f04ba8ddc`, файлы/procedures, реальный load revision1; агент правильно восстановил конфликт и отсутствие нужды reimport.19 успешных команд — чтение/диагностика, не аналитическая фаза; один exit1 — поиск отсутствующих вложенных AGENTS. Нет новой метрики/file_change/save/turn.completed. Два agent_message не заменяют артефакт.

[Outcome](../evaluation/task03/fresh-session-01/outcome.json):09:38:29.251865–09:47:33.790236 UTC, **544.547s**. TLS unexpected EOF/idle/reset OS10054, затем HTTP403 Forbidden; причина403 неизвестна.7 JSON errors и11 stderr retry messages частично описывают одни reconnect и не складываются в18 попыток. По лимиту пяти повторов без завершённого действия launcher завершил только своё дерево PID22088,cleanup0,exit1. Это технический stop, не когерентная пауза модели и не общий600s timeout.

[Subsequent load](../evaluation/task03/fresh-session-01/subsequent-load.json) отдельным процессом exit0, но побайтно совпадает со starting load: revision1. Все39 checkpoint files неизменны, добавлен pycache. [Независимый аудит](../evaluation/task03/fresh-session-audit.md) и [проверки](../evaluation/task03/fresh-session-audit-checks.json) подтверждают отсутствие новых artifact/state. Сильный критерий **NOT_VERIFIED**. Родитель не писал state в копии за свежий процесс. Эквивалентный повтор не делался; провайдер не менялся как обход недиагностированного транспорта.

## Время, ресурсы и передача

[Resource accounting](../evaluation/task03/resource-accounting.json) содержит actual boundaries/unknowns. Начало разработки08:44:32 UTC/11:44:32 МСК. Demo09:30:57–10:20:08.391526 UTC: **49мин11.392с**, до финальной revision4; gross interval включает preparation/checkpoint, transport wait, исправления/review и прерывание беседы. Финальный load после save входит в общий development interval. Fresh9мин4.547с и tests1.657s — вложенные интервалы, их нельзя складывать с общим временем. Общий конец/elapsed записаны после финальной проверки документов.

Первые41 теста M1 до расширения:0.876s; первая suite55:1.703s; финальная62:1.657s. Были focused probes/reruns по найденным дефектам; полное время подагентов не таймировалось и не суммируется. Narrow final-state review13:20:47–13:22:11МСК,84s — тоже вложено. Первый turn подагента launcher оборвался транспортно до файлов, followup завершил реализацию; это не дополнительный fresh exec. Два sandbox pip index вызова встретили WinError10013 с пятью внутренними retries каждый, затем разрешённые index/install; install с `--retries 0` около3.16s. Ошибки чтения/UTF-8 display/patch contexts записаны в worklog и не считаются успешной аналитикой.

Одно сообщение пользователя возобновило прерванную работу; resume clock09:52:24 UTC. Начало паузы неизвестно. Новых бизнес-данных/одобрения/исправлений стратегии пользователь не предоставлял. Активное время человека,tokens,charges,точный model ID и стоимость существующего доступа неизвестны; отсутствие telemetry не равно нулю. Искусственной quota не было. DeepSeek не понадобился: ключ/secret stores/adapter/new metered provider calls отсутствуют.

Следующий ограниченный development step после восстановления разрешённого host route: открыть **новый чат без этой беседы** в `C:\Users\BastaPC\Desktop\MegafonAIAgent\evaluation\task03\continuation-workspace` и дать:

> Продолжи анализ проекта demo-002 по сохранённому состоянию.

Checkpoint уже задаёт полезный разбор конфликта с расчётом/последствиями/save/load и паузой перед синтезом. После него отдельным load проверить новые refs/artifact/next_action. Сохранить архив/logs, использовать новый каталог наблюдения, не переносить в копию готовые canonical outputs. Это передача только незакрытого критерия, не повтор всей M2 работы.

Параллельно продуктовый шаг — фактические расходы/приёмка/решение владельца по v2; официальный бриф нужен для конкурсного соответствия, но не является единственной development-задачей. Ни реальный пилот, ни бизнес-одобрение, ни конкурсная готовность здесь не утверждаются.
