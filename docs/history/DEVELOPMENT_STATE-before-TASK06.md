# Состояние разработки

**TASK05_EVAL_READY_WITH_EXECUTION_GAP**, 16.11.2026. Ограниченное сравнение конфигураций A/B′ выполнено: три последовательных follow-up запроса, две ветки одного B2B-кейса, шесть первых ответов. Независимое автоматическое review: **28/28 у обоих, найденных critical errors 0**. Обычный AI baseline **NOT_RUN**: доступные no-history subagents наследуют Megafon AGENTS. Это ablation, не ordinary-chat comparison. Репозиторий обеспечил проверяемую историю/state, но содержательного и скоростного преимущества в этом срезе не показал. [Отчёт](TASK05_REPORT.md), [полные ответы и основания](TASK05_REVIEW_PACKET.md), [готовность к сдаче](SUBMISSION_READINESS.md).

Предыдущий текущий документ сохранён в [history/DEVELOPMENT_STATE-before-TASK05.md](history/DEVELOPMENT_STATE-before-TASK05.md); TASK01–04 отчёты и материалы не переписываются. 81 PASS TASK04 — исторический результат, не повторный baseline run. Финальная регрессия исправлений TASK05: **85 PASS**, без failures/errors/skips. [Команда и лог](../evaluation/task05/observations/regression-final-03/result.json), [закреплённая реализация](../evaluation/task05/implementation-final-02.json).

## Реализованный срез

Один Codex координирует LLM и tools. Python извлекает, считает, валидирует файлы и обходит явные ссылки. Существуют два учебных продуктовых кейса, версии источников/координаты/воспроизводимые вычисления, пять согласованных документов стратегий, файловая память, история решений и обязательств. Router направляет выбор, вопросы о внимании и новое evidence в decision-followup. Один координатор пишет общую память; фонового мониторинга и рассылок нет.

История выбора/оснований сохраняется append-only. Внешний документ не является authority. Withdrawal открывает review/отдельное предложение, не переписывая принятое решение и не доказывая противоположное. Scope основан на declared evidence/review/context links; неизвестная точность требует conservative review и смысловой проверки координатора. PDF block-level scope не различает две фразы внутри блока самостоятельно.

TASK05 исправил три материальные проблемы: плановое окончание больше не выдаётся за завершённое окно наблюдений; техническое влияние повторной числовой поправки не вызывает автоматического нового выбора владельца; собственный raw impact report не становится ложным calculation root. Для пересекающихся числовых review проверены оба порядка закрытия и сохранение независимого законного owner review. Новое существенное числовое основание по-прежнему требует аналитической проверки и явной эскалации. История дефектов и промежуточные FAIL сохранены. [Контроли](../evaluation/task05/controls-final.json), [review flags](../evaluation/task05/code-review-final.md), [review impact](../evaluation/task05/code-review-impact.md).

Legacy metric dates считаются планом. schedule_state отделён от window_state; фактическое observation требует evidence старта, разрешение само по себе старта не доказывает. Старая schema1 и decision.format_version=2 остаются читаемыми. Реальные approvals, участники или результаты в учебных данных не появились.

Windows/PowerShell, проектная .venv: Python 3.12.10, openpyxl 3.1.5, pypdf 7.1.0, et-xmlfile 2.0.0. Поддержаны заявленные TASK03 selected XLSX/literal calculations и простой text-layer PDF. OCR, произвольные PDF tables и визуальная проверка не заявлены. Новых зависимостей, ключей, провайдеров и глобальных изменений нет. Git checkout в этой папке отсутствует; версии закреплены SHA manifests.

## Сохранность и границы проверки

Канонические demo-001 и demo-002 остаются **revision 5 / outputs v2 / awaiting_decision**. TASK04 isolated lifecycle заканчивается revision 11 и сохранён. TASK05 использовал чистую предметную историю r3 с техническим rebase r1–2, исключив поздние ответы/evaluator notes; измеренные ветки A закончились r5. Учебные выборы/события в canonical не перенесены. [Хеши, состояние и паритет входов](../evaluation/task05/acceptance.json).

TASK04 focused recovery подтверждает безопасный published current либо явную диагностику на проверенных границах. Это не power-loss durability, multi-file transaction, multi-writer, emergency UI cancellation или exactly-once внешних эффектов. Полная crash matrix и универсальная защита от prompt injection не добавляются как вымышленные обязательные работы.

TASK05 результаты — описательные: общий inherited guidance, процедурная изоляция, небольшой синтетический набор и автоматическое review без человеческой калибровки. B′ получил те же 54 предметных артефакта, собственную историю/notes и обычные calculation tools; private JSON schema не требовалась. Tokens, charges, exact model/settings и активное время человека неизвестны. Подготовка, execution, grading и fixes учтены отдельно; пересекающиеся интервалы не складываются. [Ресурсы](../evaluation/task05/resource-accounting.json).

## Следующие ограниченные проверки

1. M5 ordinary comparison: открыть два независимых разрешённых чата с одинаковой наблюдаемой моделью в новых папках по [handoff](../evaluation/task05/README.md), проверить отсутствие Megafon guidance у B и выполнить три frozen запроса. Пакет готов, ответы ordinary B не реконструировались. При изменении сравниваемого кода нужен новый freeze; текущие fixes проверены отдельно, не подменяют benchmark.
2. Независимый carry **FRESH_HOST_SAVE_RELOAD — NOT_VERIFIED**. TASK02 сохраняет исторический узкий recovery+substantive-next-step PASS. TASK03 fresh process загрузил r1, но не создал свой аналитический артефакт/новую revision; subsequent load остался r1. TASK04 coordinator, Python load и TASK05 no-history subagents не закрывают этот критерий. TLS/reset/HTTP403 не устанавливают причину. Эквивалентный nested запуск не повторялся: нового основания для полезной поддержанной попытки нет.
3. Официальный дополнительный бриф/RQ20, финальная демонстрация, описание со скриншотами, видео до 10 минут, передача репозитория/архива, доступ жюри и подтверждение сдачи — отдельные пункты [SUBMISSION_READINESS](SUBMISSION_READINESS.md). **Official-brief conformity — NOT_VERIFIED.** Бриф не блокировал TASK05; скриншоты, запись, публикация и сдача не выполнены созданием списка.

Подлинный fresh-host handoff сохранён: `evaluation/task03/continuation-workspace` — unfinished checkpoint, без поздних answers/outputs/скопированной venv. При появлении подходящего разрешённого host открыть **новый независимый чат в этой папке** и дать:

> Продолжи анализ проекта demo-002 по сохранённому состоянию.

Сначала [аудит](../evaluation/task03/fresh-session-audit.md) и [outcome](../evaluation/task03/fresh-session-01/outcome.json). Агент должен сам завершить полезную фазу конфликта/расчёта без reimport, сохранить новую revision и артефакт; отдельный loader должен найти их. Новый каталог наблюдения обязателен, прежние logs/checkpoint не заменять. Не менять auth/provider и не обходить ограничения для устранения отказа.

Реальное бизнес-решение, бюджет и внешние действия требуют действительной инструкции уполномоченного владельца. Реальный коммерческий пилот, второй IDE и DeepSeek не обязательны для TASK05. Не было публикации, push, outreach или отправки локальных материалов новым внешним сервисам.
