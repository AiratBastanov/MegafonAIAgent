# Записи M1/M2

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
