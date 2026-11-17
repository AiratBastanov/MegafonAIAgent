# Записи M1/M2 и сопровождение решений TASK04

Все пути относительны `projects/<id>`. JSON UTF-8, ISO 8601 с timezone. Числа Decimal в расчётах сохраняются строками. Состояние разработки — `docs/DEVELOPMENT_STATE.md`; состояние продукта — только его папка.

`evidence/sources/S001/v1/source.json` хранит stable id/version, kind, actual origin, imported_at/accessed_at, input_sha256, synthetic, extraction_method, limitations, retrieval_status, ссылки с хешами на original и extract. Метаданные создаются последними. Повтор с теми же байтами и provenance возвращает reused; новая версия не затирает старую.

Извлечение: DOCX `body/b1/p1`, `body/b2/t1/r1/c1/p1`; это порядок блоков/ячеек, не страницы. CSV locator содержит физические строки, values — имена колонок. Веб содержит исходный/конечный URL, доступ, раздел, способ получения и ограничения. Неудачный read — отдельная запись действия.

M2 добавляет source kinds `xlsx` и `pdf` без миграции `schema_version=1`. XLSX locator — исходные имя листа/адрес (`'Лист 1'!C3`), selection с диапазонами/единицами/периодом и хешом файла определения сохраняется в metadata. PDF locator — физическая страница и индекс текстового фрагмента, его хеш; page label хранится отдельно. Метод с версией библиотеки, ограничения и `extracted_not_claim_verified` сопровождают извлечение. Импорт не проверяет все будущие утверждения автоматически.

В `analyze_table` для XLSX `input.sha256` по-прежнему относится к оригиналу зарегистрированной версии, поэтому прежняя прямая связь calculation→source работает без изменения валидатора. Дополнительные `provenance` и `normalization.rows[].cells` хранят source type, method/limits, extract hash, исходные ячейки, значения/типы/единицы/период. Spec закрепляется отдельным artifact. Claim о результате ссылается на calculation и source ID/version; интерпретация имеет свой kind и `derived_from`. Сценарный экономический расчёт связывают также с явными допущениями; его наличие не превращает допущения в измерения.

Минимальный draft state:

```json
{
  "schema_version": 1,
  "project_id": "example-001",
  "objective": "Цель",
  "decision_question": "Какой выбор нужен?",
  "stage": "research_complete",
  "completed": ["Проверены входы"],
  "artifacts": [{"id": "A1", "path": "evidence/note-v1.md", "sha256": "64 lowercase hex"}],
  "sources": [{"id": "S001", "version": 1, "artifact_ids": ["A1"], "synthetic": true}],
  "claims": [{"id": "C001", "kind": "source_fact", "text": "Источник сообщает...", "evidence": [{"artifact_id": "A1", "locator": "абзац 1", "source_id": "S001", "source_version": 1}], "derived_from": [], "synthetic": true}],
  "unresolved_questions": ["Неизвестны расходы"],
  "pending_actions": ["Сравнить альтернативы"],
  "next_action": "Оценить варианты на проверенных основаниях",
  "decision": {"status": "proposed"}
}
```

Создавай хеши `reference(project, relative_path, artifact_id)` из `scripts/project_state.py`, не вписывай выдуманные значения. В artifacts перечисли прямые важные версии: оригинал/метаданные/извлечение каждого использованного источника, спецификации, расчёты, постановку, outputs и review. Каждый source.artifact_ids указывает на эти же IDs. Evidence связывает claim с artifact_id и точной координатой; derived_from с другими claim IDs. synthetic=true обязателен при синтетическом основании и наследуется производными. Типы: source_fact/computed/assumption/hypothesis/forecast/recommendation/synthetic_response.

CLI `save --project projects/<id> --draft drafts/checkpoint-v1.json` проверяет draft и артефакты, назначает revision/saved_at, пишет историю `state/history/r000001.json`, сохраняет валидный `previous.json`, затем заменяет `current.json`. Артефакты предварительно записаны в новых путях. Старые версии не удалять. State не может ссылаться на mutable state-журнал.

`load` и `validate` проверяют структуру и хеши; повреждение текущего не скрывается. `load --previous` осматривает предыдущий вариант, `recover --previous` явно восстанавливает его после проверки. Временные/осиротевшие кандидаты показываются как предупреждения. Это безопасная замена одного указателя при одном писателе, не транзакция нескольких файлов, не exactly-once и не lock. Полная crash matrix отложена.

Журнал значимых действий в `state/actions.jsonl`: время, действие/инструмент, входные версии, outcome, ошибки/повторы и проверенные ссылки. Итоговый неизменяемый снимок журнала можно связать как artifact. Без рекурсивного протокола на каждое чтение. Модель, timestamps и ресурсы записывай только наблюдаемые; `null` с пояснением допустим для tokens/money/human time.

В `decision` accepted/rejected разрешены только при реальном human_confirmation со ссылкой на подтверждение; тестовая коррекция не является бизнес-решением. Автоматическая проверка формы подтверждения не удостоверяет полномочия человека.

## Расширение без переписывания старых ревизий

State остаётся schema_version=1. Старые decision без format_version читаются прежним способом. Для нового сопровождения authoritative объект `decision` имеет `format_version=2`, `question`, `proposed_option`, `owner`, прежний `status` и списки `history`, `events`, `commitments`, `metrics`, `conditions`, `reviews`; `current_outputs` сопоставляет пять имён документов с artifact IDs. Пустые списки допустимы до выбора. Метаданные не дублируются в отдельно редактируемом Markdown-реестре; readable view генерирует утилита.

Новые принятые/отклонённые бизнес-решения нельзя публиковать в legacy-формате в обход provenance. Прежние сохранённые legacy-ревизии по-прежнему читаются; это не задним числом объявленное подтверждение полномочий. Первое сохранение проекта фиксирует основания, а не принимает решение без опубликованной базы.

- **Event:** id, project_id, kind (`choice/evidence_change/completion/review`), at с offset, provenance `{kind,artifact_id,locator}` и payload. Происхождение: user_instruction / synthetic_instruction / source_material / agent_review. `fingerprint` вычисляет register_event. Повтор идентичного ID не создаёт нового результата; другой payload запрещён. Каждому choice/evidence_change/completion соответствует ровно один результат. Неполное событие не публикуется. Это идемпотентность локальной записи при одном писателе, не exactly-once внешнего действия.
- **Choice payload:** question, option, reason, owner, rejected_alternatives `[{option,reason}]`, ground_ids. Реальный выбор требует authorized=true и actor. History хранит неизменяемые поля выбора, instruction_event, basis `{revision,state_sha256}`, grounds `[{claim_id,snapshot}]`. Snapshot — полный claim на момент выбора с прежними evidence и версиями. Новый выбор закрепляется к непосредственно предыдущему опубликованному current. Artifact ID/path/hash нельзя переназначить. История/events append-only. Изменение поддержки не меняет принятое option.
- **Симуляция:** только проект с `evaluation.synthetic=true`, явным origin и изолированной папкой; synthetic_instruction создаёт status `simulated_accepted`, никогда accepted. Канонические synthetic data сами по себе не являются evaluation-разрешением выбора. Тестовый human_confirmation по-прежнему запрещён.
- **Commitment:** id, decision_id, description, owner (либо unassigned), due_at (ISO с offset либо null), due_condition, status pending/blocked/completed/cancelled, required_evidence, completion_evidence `[{artifact_id,locator}]`, blocked_by (commitment IDs), condition_ids. Завершение дополнительно требует completion_event и completion_check; зависимости должны быть завершены. Отмена сохраняет запись с явной причиной. Завершённые записи неизменяемы; коррекция отдельным событием/обязательством.
- **Metric:** id, definition, unit, denominator, observation_period, comparator/threshold (явный null допустим), needed_evidence, gate learning/scaling; window=null либо `{start,end,clock:actual|simulated}`. Прошедшее окно без evidence не даёт результата. Даты view — обязательный as-of и timezone offset ±HH:MM; тестовые часы подписываются simulated. Europe/Moscow в данном прогоне +03:00. Библиотека tzdata не требуется; исторические/будущие смены часового пояса определяет координатор явно.
- **Condition:** id, description, claim_ids, metric_ids, output_ids, next_action; unresolved_reason и review_after при наличии. Commitment связывается с ним через condition_ids; обратные review-ссылки не являются циклом доказательного вывода.
- **Review:** id, event_id, status needs_review/revised/reviewed_unchanged, reason, next_action, owner_review_required, impact и resolution_evidence. Закрытый аналитический review требует resolution_event kind=review, соответствующий результату. Исторический impact не перезаписывается. Снятие owner_review_required требует нового choice с resolves_reviews; review сам не принимает решение. Предложение меняется отдельно от history.

`evidence_change.change`: type corrected_value/superseding_version/withdrawn_support/new_contradiction/changed_assumption/freshness_review/nonmaterial; source `{id,version}`, replacement при наличии, locators (точные координаты или `*`), reason, old_ground, new_ground, applicability. Утилита валидирует версии/обходит связи, но не решает, правдив ли источник и существенен ли смысл текста. Nonmaterial нельзя использовать, чтобы скрыть реально изменённые XLSX ячейки/контекст. Числовое сравнение не отменяет отзыв или противоречие.

У claim допускаются `review_dependencies` (claim IDs, причина пересмотра без выведения) и `context_from` (контекст без распространения impact), а также status needs_review/withdrawn/superseded/contradicted и support_reason. У source_fact остаётся истинным историческое «источник сообщал», даже если текущая применимость отозвана. Координатор явно разделяет оба смысла. `artifact_dependencies:[{from,to,reason}]` задаёт ацикличные вычислительные связи между закреплёнными версиями; claims используют прежние evidence/derived_from. Outputs достигаются через conditions. Пропущенную смысловую связь ни validator, ни traversal не могут угадать.

При отказе публикации осмотри `reconcile`: валидный current является authority. Результат published означает наличие полного результата в current; absent_from_current не доказывает, что событие никогда не публиковалось. Более новая history могла остаться до публикации или после явного recovery: validated_publication_unknown требует сверки наблюдений. Invalid candidate даёт только имя/диагноз, без raw bytes. Без current loader возвращает явную ошибку; восстановления или завершения по orphan автоматически нет. Артефакт, записанный до save, не считается опубликованной работой.
