# Навигационная копия исторического документа

Источник: `docs/history/DEVELOPMENT_STATE-before-TASK04.md`. Исходные байты сохранены; здесь изменены только относительные Markdown-ссылки. Это не новый run или новое доказательство.

# Состояние разработки

**TASK03_M2_IMPLEMENTED_WITH_VERIFICATION_GAPS**,16.11.2026. [Отчёт](../../docs/TASK03_REPORT.md), [полный review snapshot demo-002 revision4](../../docs/TASK03_REVIEW_PACKET.md). M2 форматы и содержательный второй кейс реализованы; сильная проверка fresh process→полезная фаза→new state→separate reload **NOT_VERIFIED** из-за транспорта. Это не отменяет историческую приёмку TASK02 и не блокирует независимую разработку.

Работают XLSX selected ranges с координатами/типами/hidden/merged/formula-cache/единицами/периодами, literal-cell calculation с provenance и ограниченный text-layer PDF с physical pages/blocks и явными отказами. OCR/визуальный аудит/произвольные PDF tables не заявлены. Архитектура прежняя: один Codex, явные procedures, файл state, небольшие deterministic utilities. Schema1 совместима, `project_state.py` не менялся. ARCHITECTURE исправлен: corrupt state оставляет только безопасную hash/size/reason диагностику, не raw bytes.

Среда: проектная `.venv\Scripts\python.exe`,Python3.12.10,openpyxl3.1.5,pypdf7.1.0,et-xmlfile2.0.0; requirements закреплены.62 теста PASS,0skip; отдельные raw-source/arithmetic/correction/state проверки и независимое автоматическое review завершены. Три материальных code findings и два strategic findings исправлены. Человеческое review не получено. [Проверки](../../evaluation/task03/checks-final/result.json), [ресурсы](../../evaluation/task03/resource-accounting.json).

Канонический demo-001 неизменен: revision5/outputs v2/awaiting_decision,64 файла совпадают с baseline. Его пять документов и decisive evidence проверены без нового материального дефекта. Interrupted calculation из pre-correction revision2 классифицирован отдельно и не перенесён в canonical. TASK02 сохранил узкий recovery+next step PASS,41 тест и последующий transport gap; новый критерий ему задним числом не приписывается.

Канонический demo-002: revision4/outputs v2/awaiting_decision,56 artifacts,14 claims,6 source versions. Учебный B2B исходящий сервис против входящего сбора/status quo/закрытия. PDF/XLSX синтетические; две страницы Dropbox действительно меняют ограничения обещания. Коррекция поддержки30→90min сохранила прежние версии и пересчитала только затронутое: margin1500,N20остаток0 до неизвестных расходов. Рекомендация — условная ограниченная проверка; масштабирование/реальный спрос не доказаны. [Проект](../../projects/demo-002/README.md).

**Следующая ограниченная задача нового development-чата:** закрыть только наблюдение fresh phase/save/reload, когда разрешённый host route снова работает. Сначала прочитать [аудит](../../evaluation/task03/fresh-session-audit.md) и [outcome](../../evaluation/task03/fresh-session-01/outcome.json). Единственная попытка544.547s восстановила checkpoint, но TLS/reset/HTTP403 остановили её до нового артефакта. Причина403 неизвестна; нельзя бесконечно повторять, отключать ограничения, переносить auth или менять provider как обход.

Готовая чистая папка `evaluation/task03/continuation-workspace` содержит настоящий unfinished revision1,39 исходных файлов, runtime note с явным interpreter, без поздних answers/outputs/скопированной venv. Открыть **новый независимый чат в этой папке** и дать:

> Продолжи анализ проекта demo-002 по сохранённому состоянию.

Сохранённый next_action задаёт полезную фазу: разрешить конфликт PDF/XLSX, рассчитать из literal cells без reimport, сохранить вывод/новую revision, проверить load и сделать паузу до пяти стратегий. Затем отдельным процессом load найти новый артефакт и правильный next_action. Сохранить нынешние архив/logs, писать новый каталог наблюдения. Готовые canonical ответы в копию не переносить; parent state save не доказывает работу свежей модели. До доступного маршрута дополнительного эквивалентного запуска не требуется.

Другие независимые следующие действия: владелец продукта рассматривает v2, подтверждает фактические расходы/возможности/бюджет проверки; доступный официальный бриф сопоставляется с решением для конкурсной оценки. Кабинет не прочитан через web route; неизвестно, опубликован ли бриф. Это не единственная development-задача. DeepSeek отложен без ключа/адаптера/новых metered calls. Видео, публикация, push и финальная сдача не выполнены и не авторизованы TASK03.

Начало TASK03 08:44:32 UTC/11:44:32 МСК; demo09:30:57–10:20:08.391526 UTC,49мин11.392с. Общий конец/elapsed — resource-accounting.json. Интервалы пересекаются и включают ожидания/прерывание; активное время человека,tokens,charges,точный model ID неизвестны. Одно сообщение пользователя возобновило работу, бизнес-одобрение не появилось. Исторические оценки не превращаются в квоту или обещание сроков.
