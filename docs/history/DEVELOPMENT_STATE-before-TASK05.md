# Состояние разработки

**TASK04_FOLLOWUP_LOCAL_PASS**, 16.11.2026: локальное сопровождение решений и focused reliability проверены. Итог приёмки, команды и измерения — [TASK04_REPORT](TASK04_REPORT.md); читаемый generated snapshot — [TASK04_REVIEW_PACKET](TASK04_REVIEW_PACKET.md). Прежний текущий документ сохранён в [history](history/DEVELOPMENT_STATE-before-TASK04.md); TASK01/02/03 отчёты не переписываются.

Один Codex координирует анализ; Python извлекает, считает, валидирует и обходит явные ссылки. Router вызывает decision-followup при выборе, вопросе о внимании, продолжении после выбора и новом evidence. История решения/основания/инструкция сохраняются; обязательства имеют evidence завершения, условия и неизвестных владельцев/даты. View использует явные as-of/timezone/actual либо simulated часы. Фонового наблюдения и рассылки напоминаний нет.

decision.format_version=2 расширяет schema1, прежние ревизии доступны. Выбор и events append-only; source_material не является authority. Отзыв поддержки создаёт review и отдельное предложение, не переписывает принятое решение. Scoped impact различает ячейки/версии/смысловой отзыв, доказательные/review/контекстные связи; неизвестная точность означает conservative review. Пропущенную смысловую связь оценивает координатор.

Среда осталась Windows/PowerShell, проектная .venv: Python3.12.10, openpyxl3.1.5, pypdf7.1.0, et-xmlfile2.0.0. Новых зависимостей/провайдеров/ключей/глобальных настроек нет. Работают заявленные TASK03 selected XLSX/literal calculations и простой text-layer PDF. OCR/визуальный аудит/произвольные PDF tables не заявлены. PDF-пакет установлен и проверен; прежнее отсутствие в TASK01 — историческое наблюдение.

Локальный цикл выполнен в evaluation/task04/projects/task04-followup, явно производном от demo-002 revision4. Синтетический выбор, четыре обязательства, learning/scaling gates, отзыв безаккаунтного обещания и пять согласованных outputs/v3; числовая коррекция достигает экономического условия, воронка повторно используется; несвязанный материал не меняет стратегии, replay не дублирует решения. Ни один реальный пилот или рыночный результат не выполнен. Независимое автоматическое review нашло и помогло исправить материальные ошибки; оно не заменяет человека.

Канонический demo-001 сохранён revision5/outputs v2/awaiting_decision. Demo-002 теперь revision5/outputs v2/awaiting_decision: новая версия исправляет C011 review_dependencies к C013/C014 и контекст C003 для C006/C007. Все прежние входы, outputs и history1–4 сохранены. Синтетические события TASK04 в canonical не перенесены. Решения о B2B-продукте не ограничивают разработку репозитория.

81 regression test PASS в финальном полном запуске TASK04 (счётчик — наблюдение, не квота). Отдельно проверены шесть injected boundaries и отдельные Python loads: artifact-before-save, partial history, failed previous/current replacement, missing evidence и corrupt current. Loader возвращает валидный published current либо явную ошибку; recovery сохраняет только безопасную диагностику. Reconcile различает published и absent_from_current; history после recovery имеет publication_unknown. Это не power-loss durability, multi-file transaction, multi-writer, emergency UI cancellation или exactly-once внешних эффектов.

**Следующие ограниченные development-задачи:** подготовить сопоставимый небольшой M5 baseline и измерить полезность follow-up на обычных запросах без ручного знания автора; расширять M3 только по конкретным оставшимся рискам. Authority реального решения проверять при действительной инструкции владельца. Все M3/M4 целиком не объявляются завершёнными. Официальный дополнительный бриф/конкурсное соответствие, человеческое review, видео, публикация и сдача остаются отдельными работами; бриф не блокировал TASK04. DeepSeek необязателен и не подключался.

**Независимый carry: FRESH_HOST_SAVE_RELOAD — NOT_VERIFIED.** TASK02 сохраняет исторический узкий recovery+substantive-next-step PASS. TASK03 fresh process загрузил revision1, но не создал аналитический артефакт или новую state revision; subsequent load остался revision1. TLS/reset/HTTP403 не устанавливают причину. TASK04 coordinator и отдельный Python loader не закрывают критерий. Эквивалентного nested запуска не было: новых доказательств работающего разрешённого маршрута нет.

Ready handoff сохранён без изменения: evaluation/task03/continuation-workspace — настоящий unfinished checkpoint, без поздних answers/outputs/скопированной venv. При появлении подходящего разрешённого host открыть **новый независимый чат в этой папке** и дать:

> Продолжи анализ проекта demo-002 по сохранённому состоянию.

Сначала [аудит](../evaluation/task03/fresh-session-audit.md) и [outcome](../evaluation/task03/fresh-session-01/outcome.json). Агент должен сам завершить полезную фазу конфликта/расчёта без reimport, сохранить новую revision и артефакт, затем отдельный loader должен найти их. Новый каталог наблюдения обязателен; старые logs/checkpoint не заменять. Не менять auth/provider и не отключать ограничения для обхода отказа. Этот carry не является единственной следующей development-задачей.

Время TASK04, интервалы demo/development и неизвестные tokens/charges/model/human effort — evaluation/task04/resource-accounting.json. Интервалы вложены и не складываются; отсутствие telemetry не означает нулевой стоимости.
