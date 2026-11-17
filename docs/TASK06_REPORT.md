# TASK06 — проверяемый локальный пакет с открытыми пунктами

**TASK06_LOCAL_PACKAGE_WITH_GAPS**, 16.11.2026. Подготовлены переносимый release candidate, проверенный старт Python-части из новой распаковки, отдельная учебная репетиция RelayBox с коррекцией, русское описание в Markdown/PDF, изображения фактических артефактов и runbook. Независимое продолжение LLM и настоящее видео всей последовательности отсутствуют; официальный дополнительный бриф, доступ жюри и фактическая сдача не подтверждены.

## Что изменено

Существующий Codex-координатор, процедуры и runtime scripts сохранены. Новых LLM backend, провайдеров, ключей, native skills, мониторинга или бизнес-разрешений не добавлено. `evaluation/capture_checkpoint.py` получил `--portable`: текущие инструкции/tools и pinned wheels, относительная установка собственной venv вместо абсолютного interpreter владельца; старый `--python` сохраняет прежнее поведение. TASK05 frozen-v2 не менялся и остаётся PRE-FIX.

Добавлены локальные инструменты подготовки/хеширования/проверки пакета и экспорта. Runtime dependencies прежние: openpyxl 3.1.5, pypdf 7.1.0, et-xmlfile 2.0.0. Сетевой pip в новой venv отклонён WinError10013. Из существующего pip cache извлечены только эти три wheel, проверены pinned metadata/RECORD/SHA; установка без сети в новой venv прошла. Original `.venv` не используется для репетиции и первого запуска. Auth/provider/security/global instructions не читались и не менялись. [Происхождение wheel](../third_party/wheels/README.md), [команды и ошибки](../evaluation/task06/WORKLOG.md).

Исторические raw reports/runs, canonical demo-001/demo-002, TASK03 checkpoint сохранены. Архивная проверка обнаружила старые относительные ссылки после перемещения исторических материалов; 20 отдельных navigation copies разрешают 214 ссылок, включая 138 исходно сломанных. Originals не исправлялись. [Карта](../submission/EVIDENCE_MAP.md), [машинное сопоставление](../evaluation/task06/portable-links.json).

## Демонстрация и ограничения авторства

Новый `projects/task06-rehearsal`, собственная история r1–r6 и outputs/v1–v2. Начальные байты PDF/XLSX — demo-002; данные вымышлены и не официальный бриф. Все новые аналитические тексты созданы текущим координатором, а не скриптом генерации стратегии или независимым measured участником.

Обычный учебный manager request → импорт/координаты → разрешение «восемь пилотов = интерес» → 2/8=25% и 1/10=10% → четыре варианта (keep, close, исходящая передача агентствам, входящий сбор бухбюро) → обе стратегии и опровержимый план → коррекция поддержки 30→90 минут → новый расчёт/impact/согласованные v2 → follow-up с действительным as-of и synthetic=True. [Полные результаты](../projects/task06-rehearsal/README.md), [самодостаточный packet](TASK06_REVIEW_PACKET.md).

Вклад снизился 2100→1500 RUB/организацию/месяц, остаток при условных 20 организациях 12000→0 до неизвестных расходов; строго положительный с 21 вместо 15. Setup 60000, CAC/налоги/продления не потеряны. Воронка/возможности не менялись; FUNNEL1 переиспользован. Прежние C005/C007 superseded, текущие C008/C009. Согласованного бюджета/пилота/принятого решения нет; финал r6 / awaiting_decision / proposed, history бизнес-решений пустая.

Подлинная незавершённая r1 захвачена **до** дальнейшего анализа: capture завершён 15:26:21.569715 UTC, первый расчёт начат 15:26:22.449953 UTC. Handoff 46/46 SHA, без outputs, поздних коррекций и evaluator notes. Он нетронут; продолжение координатора выполнено в другой копии. [Точный handoff](../evaluation/task06/CONTINUATION_HANDOFF.md). Независимый authorised Codex-контекст не открыт: API такой операции не предоставлен, доказательств исправленного TASK03 транспорта нет. No-history механизм TASK05 не повторялся. Python load и нынешняя беседа не закрывают FRESH_HOST_SAVE_RELOAD.

## Фактические проверки

| Проверка | Наблюдение и граница |
|---|---|
| Новая распаковка prep1 | ZIP распакован в `_task06/prep1`; новая `.venv`; offline install pins, pip check и load r6 PASS. Логи `evaluation/task06/observations/clean-prep1-*` |
| Первичные материалы и арифметика | Для v1 и v2 по 39 fidelity и 16 независимых Fraction/OOXML checks PASS; не рынок и не OCR |
| История/state | r1–r6, hashes, старые источники и незатронутые расчёты доступны. Финальный loader в распаковке должен подтвердить packaged state |
| Handoff | 46/46 hashes/CRC и отсутствие поздних ответов проверены рецензентом; independent LLM completion NOT_VERIFIED |
| Описание | [Markdown](../submission/PROJECT_DESCRIPTION.md), [PDF](../submission/PROJECT_DESCRIPTION.pdf): 9 страниц, просмотренная вёрстка, 83 link annotations, 3 документных изображения; это не live Codex screenshot |
| Review | Отдельный read-only рецензент проверил demo, числа, границы, PDF и навигацию; материальные findings исправлены. [Demo review](../evaluation/task06/demo-review.md), [submission review](../evaluation/task06/submission-review.md) |
| Регрессия | Историческая финальная TASK05: 85 PASS, не новый benchmark. Проверка текущего точного final ZIP выполняется из его новой распаковки и сохраняется отдельно в `dist/validation-rc1` |
| Финальная упаковка | `dist/MegafonAIAgent-TASK06-rc1.zip`, рядом `.manifest.json`, `.contents.md`, `.sha256`. Внутри MANIFEST.json/CONTENTS.md; наблюдения exact ZIP находятся снаружи, чтобы не менять проверяемые байты |

Последняя строка и путь финальной регрессии описывают расположение проверки, а не заранее присвоенный PASS. Проверка exact ZIP должна охватывать CRC/хеши, навигацию и историческую карту, исключение credentials/venv/cache, pinned install, regression, loader/history, арифметику, PDF/PNG, сохранность исходных историй. Машинный итог и время завершения публикуются в `dist/validation-rc1/FINAL_STATUS.json` после выполнения. При изменении пакетных файлов требуется новая версия архива.

## Неуспехи и исправления

Сохранены все captured ошибки: mojibake без Encoding (повтор UTF-8); сетевой pip WinError10013 (законная offline установка); web timestamp без timezone (новый корректный import с оговоркой времени регистрации выдержки); неправильно привязанная provenance сценарного calc (save отвергнут, новый draft с отдельным источником/расчётом); направление raw→scenario metadata (исправлено новой revision); несовпадение as-of/timezone (новый view); r5 evaluation.synthetic отсутствовал (новая r6); собственный PDF file handle WinError32 (запись из памяти); отсутствие PDF annotations (Story.write_with_links); несовпадающий пересказ gate и перенос подписи (исправленный экспорт).

Попытка scoped capture: первая команда имела ошибку quoting/nonterminating errors; исправленный PowerShell helper отклонён execution policy. Обход/изменение политики не выполнялись. FFmpeg 8.0 присутствует, но видео и новый чат этим не созданы. Полный экран с посторонним содержимым не захватывался. **VIDEO_NOT_RECORDED**, [runbook](../submission/DEMO_RUNBOOK.md).

Подготовленные скрипты/описание не считаются исполненными внешними действиями. Исторические отказавшие checkpoints/transport logs и первые export versions сохранены. Рецензент только читал; общее product state писал один координатор. Пользователь не давал промежуточных реальных бизнес-решений.

## Ресурсы и сравнительная оценка

Первый clock TASK06: 15:15:38 UTC после начального чтения. Репетиция 15:23:45.600681–15:35:50.714355 UTC = **725.113674 с**, включает паузы/рассуждение/исправления/ожидания. Подготовка, demo, проверки, export и packaging учитываются в отдельных observations; overlapping интервалы не складываются. [Реестр до финальной упаковки](../evaluation/task06/resource-accounting-v1.json); поздние операции имеют собственные result.json, финальный cutoff снаружи ZIP. Точная модель/settings/tokens/charges/active human time unknown, не ноль.

TASK05 честно сохранён: A/B′ — ablation **28/28**, critical answer errors найдено 0; A **1847.658542 с**, B′ **1207.712457 с**. Содержательного или скоростного преимущества не показано. PRE-FIX freeze не заменён исправленным кодом задним числом. Ordinary B **NOT_RUN**. Новый неисполненный current-code freeze использует прежнюю компетентную baseline/inputs/3 prompts/rubric; 217/217 SHA проверены. [Передача](../evaluation/task06/ORDINARY_HANDOFF.md). Ответы ordinary baseline координатор не генерировал.

## Отдельные открытые пункты и действия владельца

- **Clean setup:** PASS для новой prep1 распаковки/venv; exact final candidate observations отдельно. Это Python-часть, не свежий LLM-host.
- **Current-release continuation:** NOT_VERIFIED; открыть новый разрешённый чат из portable r1 handoff, получить свой артефакт/save и отдельный load.
- **Historical TASK03 carry:** NOT_VERIFIED; original r1/failed logs нетронуты, повтор старого теста той же способности не нужен.
- **Ordinary baseline:** NOT_RUN; дополнительная независимая answer-blind пара по новому freeze при появлении подходящего маршрута.
- **Official-brief conformity:** NOT_VERIFIED. Предоставить документ/текст дополнительного брифа, не credentials. Общий DescriptionMegafonAIAgent.txt его не заменяет; шесть txt-guides отсутствуют локально.
- **Report/screenshots:** подготовлены Markdown/PDF и реальные рендеры, их границы явно подписаны.
- **Video:** VIDEO_NOT_RECORDED; записать настоящую полную последовательность ≤10 минут после доступного независимого продолжения.
- **Publication/jury access:** NOT_VERIFIED. Локально нет Git checkout; web GitHub дал Cache miss, не доказательство отсутствия/приватности. Публикация/upload не выполнялись; передать архив и проверить доступ получателя отдельно.
- **Actual submission:** NOT_SUBMITTED. Нужна действительная сдача и подтверждение кабинета после комплектации.

Все независимые доступные локальные шаги оформлены отдельно от этих внешних зависимостей. Главная навигация — [submission/README](../submission/README.md). Предыдущие DEVELOPMENT_STATE/SUBMISSION_READINESS сохранены в docs/history/*-before-TASK06.md.
