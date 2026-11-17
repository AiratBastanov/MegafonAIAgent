# TASK04 — сопровождение решения, пересмотр оснований и локальное восстановление

**TASK04_FOLLOWUP_LOCAL_PASS**, 16 ноября 2026. Текущий host-координатор выполнил изолированный post-decision цикл; отдельный Python-процесс загрузил **task04-followup revision11 / outputs v3** и восстановил историю выбора, четыре обязательства, открытый пересмотр и следующий шаг. [Приёмка](../evaluation/task04/acceptance.json), [generated review packet](TASK04_REVIEW_PACKET.md), [полный separate load](../evaluation/task04/separate-final-load.json).

**FRESH_HOST_SAVE_RELOAD — NOT_VERIFIED.** Рабочий координатор, подагент с контекстом и Python loader не являются независимым свежим Codex. Реальное бизнес-одобрение и соответствие официальному дополнительному брифу также не получены. Это локальная приёмка выбранного среза, не конкурсная готовность и не завершение всех M3/M4.

## Что реализовано

[Процедура decision-followup](../knowledge/procedures/decision-followup.md) включена в AGENTS, strategy-cycle и evidence-review. Обычные запросы «Мы выбрали…», «Что требует моего решения?», «Что просрочено/заблокировано?» и новые evidence ведут к загрузке state, проверке authority/оснований и короткому view. Пользователю не требуется вручную исполнять Python-этапы.

[decision_followup.py](../scripts/decision_followup.py) — детерминированная утилита `view/impact/apply/reconcile`, без модели/сети/scheduler. `apply` пишет новый кандидат, а штатный project_state save проверяет и публикует его. Единственный авторитетный реестр — `decision` внутри state; Markdown/пакет для ревью производны. Один координатор пишет память; reviewer не менял project state. Новых фреймворков, БД, провайдеров и зависимостей нет.

Расширение `decision.format_version=2` сохраняет прежнюю schema1 и читаемость старых ревизий. В history закреплены вопрос, выбранный вариант/причина, осмысленные отвергнутые альтернативы, owner, инструкция и полный снимок grounds с исходной revision/hash. Events и выборы append-only; artifact ID/path/hash нельзя переназначить. Рекомендация не принятие; source_material с «одобрением» не authority. Новые accepted/rejected требуют user_instruction и provenance; старый формат нельзя использовать для обхода новой записи. Реальные полномочия проверяет координатор, validator не аутентифицирует человека.

Обязательства хранят ответственного либо unassigned, дату либо null, условие срока, блокирующие зависимости, required_evidence, completion event/evidence/check. Дата и assertion источника не завершают работу. Метрики содержат единицы, знаменатель, период, comparator/threshold и необходимое evidence; learning и scaling gates разделены. Проверка выполняется **при вызове** на явный as-of/timezone/clock; фоновых проверок и отправленных напоминаний нет.

При изменении основания исторический выбор сохраняется, появляется review и отдельное предложение. Outcomes `needs_review`, `revised`, `reviewed_unchanged` относятся к аналитической работе; `owner_review_required` не снимается её результатом. Только новый выбор с `resolves_reviews` может снять перечисленные требования. Обязательные части события и результат проверяются в save, а не только в удобном helper.

## Явные зависимости и точность влияния

Impact использует существующие evidence/derived_from, scoped calculation selections, ацикличные artifact_dependencies, отдельные review_dependencies и context_from. Последние не распространяют изменение. Review backlinks допускаются с visited; доказательные, вычислительные и блокирующие циклы отклоняются. Проверяются неизвестные ID, проект, pinned source versions, artifact hashes и историческая база решения. Старый output не регистрировался как независимый фактический источник.

Различаются corrected_value, superseding_version, withdrawn_support, new_contradiction, changed_assumption, freshness_review и nonmaterial. Сравнение XLSX учитывает cell records, selection, единицы/период и состояние листов; совпавшие числа не отменяют семантический отзыв или противоречие. Поддержаны объявленные XLSX ranges и PDF physical-page/block ranges; непонятный locator даёт conservative review. Новее не значит надёжнее, старее не значит ложно, withdrawal не доказывает противоположное. Полноту отсутствующей смысловой связи всё равно проверяет агент.

Source inspection подтвердил дефект canonical metadata: **C011 не имел явной review-связи с C013/C014**, хотя экономику использовали тексты v2. Новая canonical demo-002 revision5 добавила эту связь, сохранив рекомендацию и awaiting_decision. C003 — широкое описание Воронки+Экономики; для C006/C007 она стала context_from, поскольку их реальные ячейки/расчёты уже закреплены непосредственно. Это предотвращает ложное загрязнение воронки при изменении E3. [Обоснование](../projects/demo-002/evidence/task04-dependency-review-v1.md).

## Наблюдённый цикл текущего host-агента

Начальный запрос TASK04 разрешил синтетическую оценку. Копия создана из фактически загруженной demo-002 revision4, с origin state/hash и отдельным project.md. Это не новый переименованный бизнес-кейс: второй distinct case и коррекция TASK03 переиспользованы. Результаты написаны текущим Codex после чтения источников; fixtures снабжали входные события, а Python записывал/проверял данные. Скрипты configure_demo/record_protocol/resolve_numeric — сохранённые операции записи этого прогона, не самостоятельный LLM и не генератор заранее заготовленных стратегий.

| Наблюдение | Опубликованный результат и evidence |
|---|---|
| Подготовка и определения | r1–2: копия, origin, шесть метрик, четыре условия; [demo-prepare](../evaluation/task04/observations/demo-prepare/result.json), [определения](../evaluation/task04/observations/demo-definitions/result.json) |
| Синтетический выбор | r3: OWNER-01, simulated_accepted, основания r2 и четыре обязательства. Принята только учебная подготовка при внутреннем режиме до приёмки/бюджета. [Инструкция](../evaluation/task04/projects/task04-followup/inputs/owner-instruction-v1.md), [actual apply](../evaluation/task04/observations/demo-choice-apply/stdout.txt) |
| Проверки внимания | 17.11 12:00+03 — due; 18.11 12:00+03 — K-CAPABILITY overdue, K-BUDGET unassigned/blocked без фиктивной просрочки. Оба времени simulated. [Первый view](../evaluation/task04/observations/followup-at-deadline/stdout.txt), [второй view](../evaluation/task04/observations/followup-overdue/stdout.txt) |
| Завершение по evidence | r4: выполнен только K-PROTOCOL по реально созданному [локальному протоколу](../evaluation/task04/projects/task04-followup/evidence/followup-protocol-v1.md); испытаний продукта/рынка не было |
| Отзыв поддержки и trust boundary | r5–6: зарегистрирован S006, прочитан host, отвергнута поддельная authority; impact достиг обещания/условий/пяти outputs. r6 — needs_review. [Источник](../evaluation/task04/projects/task04-followup/inputs/mock-capability-withdrawal-v1.txt), [наблюдение](../evaluation/task04/projects/task04-followup/evidence/trust-observation-v1.md), [impact](../evaluation/task04/projects/task04-followup/evidence/withdrawal-impact-v1.json) |
| Содержательная коррекция | r7: host написал пять outputs/v3; review revised, owner_review_required=true. Исторический OWNER-01 не переписан. [Результат](../evaluation/task04/projects/task04-followup/evidence/withdrawal-review-v1.md) |
| Числовая ветка | r8–9: существующая 30→90 коррекция достигает экономического условия. Текущая S002@2 E3 проходит C014→C011 review_dependency. C007/funnel не затронут; исход reviewed_unchanged, v3 не переписаны. [Числовая сверка](../evaluation/task04/projects/task04-followup/evidence/economic-recheck-v1.json), [содержательный вывод](../evaluation/task04/projects/task04-followup/evidence/economic-review-v1.md) |
| Несущественный материал и повторы | r10: S007 имеет affected=[]; outputs/claims сохранены. Повтор OWNER-01/WITHDRAW-01/NONMATERIAL-01 — no-op, один выбор/четыре обязательства. Чужой project_id отклонён. [Проверка](../evaluation/task04/projects/task04-followup/evidence/nonmaterial-check-v1.json) |
| Финальное сохранение и отдельный процесс | r11, state hash `45fe4d5ef197852323af3b34294e6bf490294e3eaf3ad0a9ca44c049414269c3`; load/view восстановили историю, активный пересмотр и next_action. На 19.12 simulated окно M-TIME ended_evidence_required, K-CAPABILITY не completed. [JSON view](../evaluation/task04/separate-final-followup.json) |

Команды и реальные timestamps записывались во время выполнения в [observations](../evaluation/task04/observations), [actions.jsonl](../evaluation/task04/actions.jsonl) и неизменяемые state histories. Event times внутри оценки обозначают сценарное время, которое отличается от фактических timestamps исполнения; часы ОС не менялись. Таблица выше — последующая сводка сохранённых наблюдений, не вымышленная conversational trace.

Отзыв относится к последней части S001@1 physical-page:1/block:5: «recipient needs no account». S006 не доказывает обязательность аккаунта и не отзывает сам по себе 2 GB/7 суток. V2 предлагал участникам отсутствие аккаунта и демонстрацию такого скачивания; v3 снимает обещание и требует проверки фактического способа доступа перед предложением/пилотом. Product, communication и validation согласованы; situation/options показывают изменённое основание и сохранённые альтернативы. Полные пять текстов и фрагменты до/после включены в review packet.

Экономика: C3=3000 RUB/месяц, D3=600, E3=30→90 минут, F3=600 RUB/час, G3=30000 RUB/месяц, H3=60000 RUB setup, I3=N20. `C3−D3−E3×F3/60`: 2100→1500; `N×вклад−G3`: 12000→0 до неизвестных расходов. Это синтетические допущения S002@1/2, а не новые измерения. Decimal-сверка совпала с прежними ECON-v1/v2; текущий расчёт уже исправлен, поэтому новая его версия не создана. Воронка S002@1 `'Воронка'!C3:F4` и CALC-FUNNEL-v1 сохранены с исходными хешами.

Пять минут у ≥7/10 — gate обучения, не обоснование 3000 RUB/месяц. Сопровождение отдельно удерживает missing частоту передач, пользу клиенту, продления, полную стоимость услуги всем пробам и приобретения клиента. Денежная ценность минуты не выдумана, missing не равен нулю. Решение владельца — стоит ли получать недостающее знание/назначать ответственного либо оставить внутренний режим, а не автоматически масштабировать.

## Recovery и согласование прерванного действия

До изменения прочитаны actual project_state и test_state; действующий протокол публикации не заменён. Добавлены проверки недостающих границ и completeness event records. [Harness](../evaluation/task04/check_recovery.py), [финальные результаты с raw loader outcomes](../evaluation/task04/recovery-final/results.json).

| Честно injected граница | Что увидел отдельный loader | Безопасный исход |
|---|---|---|
| Артефакт записан, save ещё не вызван | r2 валидна, event отсутствует | Осмотр и проверка файла, затем r3 с одним событием |
| Частичная history r3 и leftover tmp | r2 валидна, warnings; candidate invalid | Сверка, новый save в r4, неполная r3 не принята |
| PermissionError при замене previous | current r2 и previous r1 валидны | Сверка candidate, повтор в r4, событие одно |
| PermissionError при замене current | current r2 и previous r2 валидны | Неопубликованная кандидатная работа не завершена; после сверки r4 |
| Пропавший referenced evidence после публикации | Явная ошибка, previous r2 валидна | Explicit recover вернул r2; файл fixture сохранён отдельно, не удалён |
| Повреждённый current с искусственным секрет-маркером | Явная ошибка, previous r2 валидна | Explicit recover r2, hash/size/reason диагностика без raw bytes/маркера |

Каждый значимый исход подтверждён отдельным Python subprocess. После отказа не запускали повтор вслепую: сначала inspect/reconcile, проверка candidate/артефактов, затем новая публикация. Reconcile published означает полный результат в current. **Absent_from_current не означает «никогда не публиковалось»**: более новая history после recovery имеет validated_publication_unknown. Первый harness сохранил слишком сильную формулировку; reviewer обнаружил её на действительно опубликованной r3, она исправлена и повторно проверена в recovery-final. Старый result оставлен для аудита.

Это injected Python/OSError/PermissionError и настоящие локальные файловые операции Windows, не отключение питания или исследование конкретного антивируса/файловой системы. Не заявлены multi-file transaction, power-loss durability, несколько писателей, аварийная UI-отмена или exactly-once внешних эффектов. Реальных внешних действий не было. [Python os.replace](https://docs.python.org/3.12/library/os.html#os.replace) использован только для уточнения модели операции; упоминание атомарности в документации не расширяло эти наблюдаемые гарантии.

## Проверки, независимое review и исправления

Финальная полная команда:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

**81 test PASS, 0 failures/errors/skips**, unittest 4.975 s, измеренный wall interval wrapper 5.719 s. [Полный log](../evaluation/task04/observations/regression-final-02/stderr.txt), [команда и время](../evaluation/task04/observations/regression-final-02/result.json). Это 62 прежних теста, 17 follow-up checks, один suite с шестью recovery сценариями и один новый legacy-approval guard; счётчик не был целевой квотой. Перед дополнительным guard был полный успешный 80-test запуск. Последний отдельный load после guard также нашёл r11.

Действительно выполненные характерные команды (полные аргументы — в result.json наблюдений):

```powershell
.\.venv\Scripts\python.exe scripts/decision_followup.py apply --project evaluation/task04/projects/task04-followup --event inputs/owner-choice-v1.json --draft drafts/owner-choice-v1.json
.\.venv\Scripts\python.exe scripts/project_state.py save --project evaluation/task04/projects/task04-followup --draft drafts/owner-choice-v1.json
.\.venv\Scripts\python.exe scripts/decision_followup.py view --project evaluation/task04/projects/task04-followup --as-of 2026-11-18T12:00:00+03:00 --timezone +03:00 --clock simulated --markdown
.\.venv\Scripts\python.exe evaluation/task04/check_recovery.py evaluation/task04/recovery-final
.\.venv\Scripts\python.exe evaluation/task04/check_acceptance.py
.\.venv\Scripts\python.exe evaluation/task04/make_review_packet.py
```

Скрипты записи/приёмки намеренно не перезаписывают свои результаты. Не запускать весь наблюдённый цикл второй раз поверх существующей evaluation; для нового прогона нужна отдельная копия/папка. Обычный read-only view/load можно повторять. После воспроизведения в иной среде требуется новая запись actual interpreter/dependencies.

[Независимый автоматический reviewer](../evaluation/task04/independent-review-v2.md) читал код/источники/пять v3 outputs, воспроизводил проблемы на копиях в памяти, не писал общий state. Существенные исправления:

- Artifact-only evidence и declared source→artifact dependency теперь участвуют в impact; scoped reuse не теряется.
- Одинаковые ячейки не отменяют withdrawal/contradiction/freshness; units/period/hidden scope и неизвестный остаток locator требуют проверки.
- Исторические grounds закреплены к прежним artifact bindings; один instruction event не принимает два решения; status, payload и provenance связаны.
- Review нельзя удалить или снять owner requirement без нового выбора; helper применяет resolves_reviews только к указанным IDs.
- Неполные choice/change/completion/review не публикуются; completion и resolution сверены с результатом события.
- Reconciliation после recovery больше не отрицает возможную прежнюю публикацию; generic view не придумывает приоритет неподтверждённого внешнего обещания без соответствующего основания.

Reviewer наблюдал один failing regex test: удаление review уже безопасно отклонялось, но сообщение поменялось из-за более ранней проверки. Ожидание исправлено, целевые тесты прошли. Последний независимый snapshot проверил 15 tests; затем координатор добавил отдельные regression checks и запрет новой legacy-approval записи, проверенный финальным полным набором. Их нельзя приписывать прежнему snapshot reviewer. Содержательное review не нашло новых материальных противоречий пяти v3 текстов. Это автоматический обзор, не human acceptance.

Новый trust scenario — локальный **mock tool response**, не реальный вызов провайдера. Host прочитал фальшивые команды сменить правила/проект и «одобрить» работу, оставил их данными и продолжил только применимый отзыв. Детерминированные authority/scope checks отказали. Одно наблюдение агента не доказывает универсальную prompt-injection устойчивость; parser/unit test не выдаётся за поведение LLM. Реальные секреты, адресаты и отправки не использовались.

## Сохранность, milestones и открытые критерии

[Acceptance manifest](../evaluation/task04/acceptance.json): demo-001 **64/64 файла неизменны**; TASK03 continuation **39/39**, fresh-session-01 logs **13/13** неизменны (pycache исключён из первоначального manifest). У demo-002 сохранены исходные 77 файлов по прежним путям или явно указанным версиям: current r4 — history/r000004, previous r3 — history/r000003, прежний README — evidence/readme-before-task04. Новая revision5 содержит только обоснованную metadata correction; все inputs/calculations/outputs v1/v2 неизменны. Обе canonical decision — awaiting_decision. Валидированы все history1–5 canonical и history1–11 evaluation.

| Требование | Покрытие TASK04 | Что не утверждается |
|---|---|---|
| M4/E08 follow-up и пересмотр | История/authority/commitments/metrics/triggers, отзыв свойства и экономические пути, affected/unaffected, новые согласованные outputs | Реальное принятие бизнес-решения, исследование рынка и все возможные типы бизнес-ситуаций |
| M4/E10 второй distinct case | Переиспользован TASK03 demo-002, границы проектов дополнительно проверены | Новый третий кейс или повтор M2 |
| M3/E07 reliability | Шесть focused injected boundaries, отдельные loaders, безопасная диагностика и reconciliation | Полная crash matrix, power loss, concurrency/внешнее exactly-once |
| M3/E09 trust | Новый mock-tool сценарий, actual host observation и deterministic tests | Универсальная защита LLM/всех форматов и интервью без реального согласия |
| M5 review/E04/E05 | Независимый кодовый/содержательный обзор и исправления | Сравнительный baseline/доказанная экономия относительно обычного чата |
| Сильный fresh-host criterion | **NOT_VERIFIED**, отдельный carry | Рабочий coordinator/Python loader не заменяют fresh Codex |
| Human business approval | **Не получено**, canonical awaiting_decision | Synthetic instruction не даёт реальных полномочий |
| Official additional brief conformity | **NOT_VERIFIED / pending** | Бриф не получен/не сопоставлен; это не блокировало TASK04 |

TASK02 сохраняет исторический узкий fresh-process recovery + substantive-next-step результат. TASK03 сообщил supported PDF/XLSX, 62 PASS, demo-002 r4/v2 и demo-001 r5; свежий процесс тогда восстановил r1, но не создал нового аналитического артефакта/state. TLS/reset/HTTP403 не установили причину. Эквивалентного nested запуска TASK04 не было: новых сведений о пригодном разрешённом entry point нет. Auth, credentials, ограничения и провайдер не менялись.

Готовый [handoff TASK03](../evaluation/task03/fresh-session-audit.md) и `evaluation/task03/continuation-workspace` сохранены. При доступном разрешённом host — новый независимый чат без наследования, обычная просьба продолжить demo-002, собственная полезная фаза/save и отдельный load новой revision в новом каталоге наблюдения. Это самостоятельная будущая проверка, не скрытое условие TASK04 local pass.

## Время, ресурсы и следующий шаг

Начало разработки зафиксировано clock tool **11:36:25 UTC / 14:36:25 МСК**. Demo: **11:53:15.830232–12:16:16.284853 UTC**, 1380.454621 s (23 мин 00.455 s), до отдельной локальной приёмки. Полный development end/elapsed, интервалы фактических команд, review, повторов и исключений — [resource-accounting.json](../evaluation/task04/resource-accounting.json). Demo/review/tests вложены в development и не складываются с ним. Event clocks будущих дат не участвуют в учёте затраченного времени.

Наблюдаемые технические исключения: один неверный compound apply_patch для документа отклонён без изменения файла, затем применён обычный Update; один diagnostic stdout с mojibake при legacy encoding не менял источники. Рабочие CLI явно выводят UTF-8, separate loaders проверяли legacy PYTHONIOENCODING. Исправления/retries review и recovery описаны выше; одинаковых бесполезных fresh-launch повторов нет. [Среда](../evaluation/task04/environment.json): Windows11, Python3.12.10; PowerShell5.1.26100.9818 наблюдён непосредственно; версии пакетов остались прежними.

Один независимый reviewer, существующий Codex и локальные Python tools использовали текущий доступ. Точный model ID, tokens, charges и активное время человека **неизвестны**; нулевая стоимость не выводится. После исходного TASK04 новых сообщений/ручных бизнес-решений не поступало. Публикации, push, изменение видимости, контакты, реальные эксперименты, новые платные сервисы и DeepSeek integration не выполнялись.

Из предложенных implementation references фактически использована только первичная документация Python os.replace. Шесть prompting references не были найдены в доступном списке файлов workspace и не объявлялись прочитанными; чужие каталоги ради них не исследовались. Отсутствие этих копий и официального брифа не блокировало реализацию.

Следующий ограниченный development шаг — небольшой сопоставимый M5 baseline обычных follow-up запросов и измерение полноты/полезности при одинаковых условиях. Fresh-host handoff выполняется отдельно, когда есть рабочий разрешённый маршрут. Следующий продуктовый шаг остаётся решением действительного владельца на реальных основаниях, а не запуском пилота агентом.
