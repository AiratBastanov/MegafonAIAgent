# TASK04 — независимое автоматическое ревью, проход 2

16 ноября 2026 года. Проверяющий: отдельный агент `/root/independent_review`, с контекстом родителя. Это автоматический обзор, не человеческая приёмка и не независимый fresh-host continuation. Начало наблюдаемого прохода: 11:59:58 UTC / 14:59:58 МСК. Проверены промежуточные файлы до завершения TASK04; найденные ниже дефекты переданы координатору для исправления.

Изменён только этот отчёт. Реализация, канонические проекты и evaluation state проверяющим не изменялись. Воспроизведения выполнялись на копиях данных в памяти; unit tests использовали собственные временные fixtures.

## Проверенный материал

- `scripts/decision_followup.py`, интеграция validator/transition в `scripts/project_state.py`, `tests/test_followup.py`.
- `evaluation/task04/check_recovery.py` и фактический `recovery-01/results.json` с Windows/Python subprocess loader.
- Изолированный `task04-followup`: загруженная revision 7, одна история `OWNER-01-decision/simulated_accepted`, `review-WITHDRAW-01/revised` с `owner_review_required=true`.
- Все пять `outputs/v3`, прежние канонические `demo-002/outputs/v2`, исходный PDF extract S001@1 physical-page:1/block:5, S006 mock response строки 2–3, текущие C001/C007/C011/C013/C015–C018 и локальный `followup-protocol-v1.md`.

## Перепроверка первоначальных замечаний

1. Artifact-only evidence теперь достигает claim/condition/output; первичный false negative исправлен.
2. Одинаковые значения ячеек больше не отменяют withdrawal, contradiction и freshness review; исправлено.
3. XLSX comparison теперь учитывает selection и sheet metadata; неоднозначный остаток locator возвращает неизвестную точность, а не уверенное отсутствие влияния; исправлено.
4. Прямые исторические artifact/source bindings сверяются с basis; transition сохраняет прежние artifact ID/path/hash; исправлено для format_version=2.
5. Повтор instruction_event не создаёт два history решения; event choice payload сверяется с записью; основной дефект исправлен, однако статус принятия/отклонения ещё не связан — R2-01 ниже.
6. Удаление review отклоняется; снятие owner review требует нового choice event; основной дефект исправлен.
7. Choice/evidence_change/completion без обязательного результата теперь отклоняются. Review event ещё допускает неполный результат — R2-03.
8. Причина приоритета теперь выводится из активных review/condition/commitment, без фиксированного утверждения о внешнем обещании; исправлено.

## Оставшиеся материальные находки

### R2-01 — P1, статус отказа не связан с записью принятия

В `validate_extensions` сравнение history и event.choice проверяет question/option/reason/owner/alternatives/ground_ids, но не status. В памяти на копии evaluation revision 7 событие преобразовано в искусственную user_instruction с `choice.status='rejected'`, а history и decision получили `accepted`. Корректный fingerprint и форма human_confirmation заданы только в этом искусственном объекте. `project_state.validate_state` успешно принял несовпадение.

Необходимо проверять совпадение accepted/rejected с инструкцией, сохраняя отдельное правило simulated_accepted. Эта проверка должна находиться в validator, а не только в apply helper.

### R2-02 — P1, source_material может закрыть аналитический review через draft

Копия действительного review получила resolution event `kind=review`, `provenance.kind=source_material`, статус `reviewed_unchanged`, reason/next_action и существующий evidence ref. `owner_review_required` оставлен true. `validate_state` и `validate_transition` приняли объект. Путь `apply_event` такое происхождение запрещает, однако обычный draft/save обязан иметь ту же границу.

Нужна проверка provenance resolution event в validator. Аналогично completion_evidence, completion_check и commitment_id следует связывать с payload completion event, а не только с его видом.

### R2-03 — P2, review registration ещё выдаётся за завершённый результат

К revision 7 в памяти добавлен event `kind=review`, `provenance.kind=agent_review`, известный review_id, но без поля resolution и без изменения текущего review. `validate_state` и `validate_transition` успешно завершились. При публикации reconcile признал бы event выполненным.

Проверить полноту payload и применение последнего результата соответствующего review. При этом прошлые resolution events нужно сохранять после последующих пересмотров.

### R2-04 — P1/P2, опубликованный затем восстановленный snapshot назван неопубликованным

Фактический harness `corrupt_current` сначала публикует revision 3, затем повреждает current и явно восстанавливает revision 2. Вызов `reconcile('evaluation/task04/recovery-01/corrupt-current','W')` вернул:

```json
{"outcome":"not_published","candidates":[{"revision":3,"status":"validated_unpublished"}]}
```

Это слишком сильное утверждение: один history snapshot не различает неудачную публикацию и ранее опубликованную ревизию после recovery. Достаточно честно отметить отсутствие события в текущей версии и неизвестность прежнего publication outcome; не требуется усложнять систему транзакциями. Нужна проверка reconciliation после recovery, а не только перед повтором failed save.

### R2-05 — P1, прямые artifact dependencies от source не запускают обход

Минимальная допустимая цепочка в памяти: source S1@1 владеет A1; `artifact_dependencies=[{from:A1,to:CALC,reason:'Uses source'}]`; C1 имеет evidence на CALC. Withdrawal S1@1 с locator `*` дал `affected=[]`. Source artifacts сами не являются корнями, а CALC без JSON поля source не распознаётся специальным расчётным путём.

Объявленная dependency должна работать и без встроенной calculation provenance. Для source artifacts с такими связями нужен консервативный root; для точных mapped-cell calculations сохранить проверяемое selective reuse.

## Отдельный запуск тестов

Команда 16.11.2026 около 12:02 UTC:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_followup.py -v
```

Наблюдение: 12 tests, 0.874 s, 11 PASS, 1 FAIL, exit 1. Failure — `test_review_cannot_erase_human_requirement`: удаление review безопасно отклоняется более ранней проверкой «Неполное событие evidence_change», а regex ожидает «удалить требование». Это расхождение ожидания теста и безопасного порядка валидации, а не разрешённое удаление review. Координатору передано исправить ожидание и повторить затронутые проверки. Число тестов не является целевой квотой.

## Содержательное ревью v3

Материальных противоречий в пяти прочитанных v3 документах не обнаружено:

- S001 block 5 действительно содержит recipient needs no account; S006 снимает поддержку только этой части, не доказывает обратное и не отзывается автоматически на пределы 2 GB/7 дней.
- Продуктовая и коммуникационная стратегии снимают обещание безаккаунтного доступа; новый C016 остаётся предложением, исторический выбор не переименован в новое одобрение.
- ECON-v2 используется как условный прежний сценарий: 3000−600−90×600/60=1500, N20 даёт ноль до неизвестных затрат. Отзыв функции не выдан за новое измерение расходов. При иной конфигурации требуется новое основание.
- Порог пяти минут отделён от цены 3000 RUB; частота, ценность, продления, полные затраты всем пробам и CAC остаются неизвестными и требуют собственных evidence.
- Воронка S002@1/C007 остаётся применимой. Реальные клиенты/платежи/испытания не выдуманы; clock=simulated не превращён в прошедший реальный эксперимент.
- Окна 30 суток, доставка до конца окна и отдельный оплаченный месяц/продление согласованы; learning gates не разрешают масштабирование.
- K-PROTOCOL имеет подходящий локальный аналитический документ; это не завершение K-CAPABILITY и не production-приёмка.

В проекте ещё выполняется числовая/нематериальная ветка и финальное сохранение, поэтому этот проход не подтверждает всю локальную приёмку TASK04. Он также не подтверждает полную защиту LLM от prompt injection, power-loss durability, многописательность, exactly-once эффекты, бизнес-одобрение или официальный brief. Fresh-host criterion остаётся отдельным NOT_VERIFIED до собственного наблюдения.

Tokens, стоимость модели и время человека для этого автоматического обзора недоступны; нулевая стоимость не заявлена. Интервал этого обзора входит в общий интервал разработки и не должен добавляться к нему как отдельное непересекающееся время.

## Дополнение: исправления и окончательная проверка этого прохода

Координатор исправлял файлы во время обзора. Первые находки выше относятся к промежуточным bytes и сохраняются как история ревью. В 12:04–12:05 UTC проверены новые bytes; результаты повторных воспроизведений от 12:05:27 UTC:

| Находка | Проверка после исправления | Результат |
|---|---|---|
| R2-01 | Искусственный event rejected / history accepted на копии текущего state | `StateError`, подмена отвергнута |
| R2-02 | source_material resolution event через candidate validator | `StateError`, поддельное review отвергнуто |
| R2-03 | Review event без resolution | `StateError`, неполное событие отвергнуто |
| R2-04 | Reconcile W в фактической recovery-01/corrupt-current после recovery | `absent_from_current`, r3=`validated_publication_unknown`; прошлую публикацию больше не отрицает |
| R2-05 | Source A1 → declared artifact dependency CALC → claim C1 | Затронуты `artifact:CALC` и `claim:C1`; путь восстановлен |

Дополнительно статически замеченный незавершённый helper-путь `choice.resolves_reviews` уже исправлен координатором к моменту воспроизведения. На копии evaluation revision 8 вызван `apply_event` с новым синтетическим выбором и указанным review ID: `owner_review_required` стал false. Этот новый выбор существовал только в памяти проверяющего, не публиковался и не является бизнес-одобрением. Исходная история сохранилась.

Повтор той же команды unit tests в 12:04 UTC: **15 PASS**, 1.002 s, exit 0. После изменения helper — ещё один целевой запуск, завершившийся к 12:05:43 UTC: **15 PASS**, 1.015 s, exit 0. Проверка была повторена из-за новых исправлений, не ради увеличения счётчика. Координатор добавляет отдельный regression test нового выбора; будущий тестовый файл не входит в приведённый snapshot.

Проверенный snapshot без Git commit, SHA-256 на 12:05 UTC:

| Файл | SHA-256 |
|---|---|
| scripts/decision_followup.py | `69e1fd778d88842da948112ca8626b94cc68d7d36ee5923af41efaf67b084083` |
| scripts/project_state.py | `a731555fe6315577e619991808cac0a54ec9298b1438411ae22b714c651a43f2` |
| tests/test_followup.py | `205b999da8ade0ceec6f71145463462cf57c16206332b19d0364e829d1ac3fdb` |
| evaluation/task04/check_recovery.py | `bd58f035fd691176dd60b923818c39c0bddeef7f8de165de6039b771f07ed6c8` |

На этом snapshot все материальные находки R2-01–R2-05 закрыты в проверенных границах; последняя целевая выборка не выявила нового материального дефекта. Миграция старого decision следует процедуре: отдельная публикация format_version=2 до принятия выбора. Полную финальную TASK04-приёмку, неизменность canonical-пакетов, последующий итоговый loader и review packet проверяет координатор; завершённость всей задачи здесь не объявляется.

Наблюдаемый интервал второго прохода до последней проверки: 11:59:58–12:05:43 UTC, 5 минут 45 секунд, внутри разработки; он не складывается с общим elapsed. Сохранение этого дополнения выполнено непосредственно после проверки. Ограничения независимости, ресурсов и fresh-host статуса остаются прежними.
