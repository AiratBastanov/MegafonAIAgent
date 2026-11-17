> Исторический документ. Статусы относятся ко времени его создания; актуальный итог — в материалах жюри.

# Готовность локального пакета и отдельные пункты приёмки

16.11.2026 — **TASK06_LOCAL_PACKAGE_WITH_GAPS**. Пакет подготовлен для проверки, полная готовность конкурса не заявляется. Предыдущая версия сохранена в [history](../../docs/history/SUBMISSION_READINESS-before-TASK06.md).

| Область | Наблюдаемый статус и оставшийся шаг |
|---|---|
| Clean setup Python-части | Новая распаковка prep1, собственная venv, offline pinned install/pip check/load r6 PASS. Финальная проверка точного rc1 ZIP и regression — отдельно в dist/validation-rc1/FINAL_STATUS.json. Старую .venv не копировали; LLM session этим не проверена |
| Демонстрация текущего кода | Новый учебный task06-rehearsal: r6, обе стратегии, четыре варианта, план, коррекция 30→90, сохранённая пауза. Цикл координатора выполнен; обязательный независимый участок продолжения открыт |
| Current-release continuation | **NOT_VERIFIED**. Portable r1 handoff создан до расчётов/ответов, 46/46 SHA проверены. Нужен новый независимый разрешённый Codex-context: свой артефакт + new revision + отдельный load |
| Historical TASK03 carry | **NOT_VERIFIED**. Original r1 и failed logs сохранены; новый процесс тогда загрузил state, но не опубликовал содержательный результат. Повтор старого теста той же способности не требуется |
| Ordinary baseline | **NOT_RUN**. TASK05 A/B′ — ablation 28/28 и большее время A. Новый current-code freeze готов без ответов; нужны две независимые answer-blind стороны и проверенные инструкции B |
| Официальный дополнительный бриф / RQ20 / M6 | **NOT_VERIFIED**. Нужен официальный текст/документ и сопоставление. Невозможность web доступа не доказывает непубликацию/одобрение альтернативы; общий кейс не заменяет brief |
| Описание / изображения | Markdown + PDF (9 страниц, 83 действующие annotations), три legible PNG реальных артефактов; рендеры не выдаются за UI/run. Независимое review закрыто, человеческое review не заявлено |
| Видео ≤10 минут | **VIDEO_NOT_RECORDED**. FFmpeg есть, полного поддержанного пути нового чата/захвата нет; PS helper запрещён execution policy, bypass не применялся. Runbook/capture checklist готовы |
| Архив | Versioned rc1 ZIP, SHA/manifest/index; инструкции/knowledge/scripts/tests/wheels/demo/evidence включены, venv/cache/credentials/recursive dist исключаются. Итог exact archive checks находится рядом с ZIP |
| Публикация / доступ жюри | **NOT_VERIFIED**. В папке нет Git checkout; GitHub web Cache miss не подтверждает публикацию или её отсутствие. Отдельно передать архив и проверить доступ получателя |
| Фактическая сдача | **NOT_SUBMITTED**. Публикаций/upload/messages не было. Нужны готовые внешние пункты и подтверждение кабинета при сдаче |
| Канонические бизнес-решения | demo-001/demo-002 r5 / outputs v2 / awaiting_decision, без новых approvals. Репетиция также proposed; нет реального пилота, бюджета или контактов |

Точные пути: [страница жюри](../README.md), [описание PDF](../PROJECT_DESCRIPTION.pdf), [TASK06 report](../../docs/TASK06_REPORT.md), [review packet](../../docs/TASK06_REVIEW_PACKET.md), [handoff](../../evaluation/task06/CONTINUATION_HANDOFF.md), [ordinary handoff](../../evaluation/task06/ORDINARY_HANDOFF.md), [runbook](../DEMO_RUNBOOK.md).

Малая синтетическая выборка и automatic review без human calibration ограничивают выводы. Declared-links impact нуждается в смысловой проверке; один писатель, snapshots, отсутствие OCR/произвольной PDF-вёрстки/фонового мониторинга. Tokens/charges/exact model/settings/active human time unknown. Полная crash matrix, универсальная injection-защита, реальный коммерческий пилот, второй IDE и DeepSeek не добавлялись как вымышленные обязательства.
