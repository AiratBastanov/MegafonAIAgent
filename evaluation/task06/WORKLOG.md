# TASK06 — журнал значимых действий

Время записывается в UTC с offset; для показа пользователю Europe/Moscow = UTC+03:00. Токены, списания, точная модель/настройки и активное время человека не предоставлены. Пересекающиеся интервалы не складываются.

- 2026-11-16 15:15:38 UTC — первый clock после начального чтения. Подтверждены TASK05 ablation 28/28 и прежние границы. Первое чтение через PowerShell без Encoding дало mojibake; повторено явно UTF-8, исходные файлы не менялись.
- Подготовка: проверены CLI help/version, PATH, доступные tools и установленные локальные средства. Независимый рецензент требований работал только чтением. Секреты/глобальная конфигурация не читались.
- Веб-доступ: кабинет брифа недоступен через web open; GitHub URL вернул Cache miss. Это не свидетельство отсутствия брифа или репозитория. Текущая папка не Git checkout.
- Решение о маршрутах: прежние TASK03 HTTP403 и TASK05 inherited guidance сохранены; эквивалентный nested запуск и повтор no-history probe не выполняются. Независимое продолжение и ordinary baseline пока не исполнены.

Дальнейшие команды, начало/конец, stdout/stderr/exit — `observations/*/result.json`. Это интервалы subprocess, не полное время аналитической работы. Материальные исправления и итоговая упаковка дописываются ниже.

- 15:22–15:23 UTC — сетевой pip в новой среде запрещён WinError10013. Найдены три существующих wheel в pip package-body cache, проверены pinned metadata/RECORD/SHA; offline установка и pip check успешны. Ни старую venv, ни HTTP credential headers не копировали/читали.
- 15:23:45.600681–15:35:50.714355 UTC — репетиция в новой папке. Пауза r1, текущие расчёты, v1 стратегии, синтетическая коррекция, impact, v2, r6 и actual follow-up. Wall interval 725.113674 с, с рассуждением/паузами. Независимый LLM-run отсутствует.
- Capture r1 закончился 15:26:21.569715 UTC; расчёт начался 15:26:22.449953 UTC. Копия не редактировалась позже. Handoff 46/46 SHA подтверждён отдельным review.
- Сохранены отклонённые операции: timestamp без timezone; calc-source provenance ошибочно присвоена сценарию (save не прошёл); as-of UTC при timezone +03:00; first capture PowerShell quoting (nonterminating errors даже при exit0); исправленный PS helper отклонён execution policy. Обходов ограничений нет.
- Новая r4 исправила направление metadata raw→scenario; r6 исправила synthetic label в view. Предыдущие revisions/raw output сохранены. Независимый reviewer подтвердил арифметику и закрытие metadata finding.
- Отдельный ordinary-current-v1: новый freeze 217 файлов, corrected code и прежние предметные inputs/prompts; NOT_RUN. Старый frozen-v2 PRE-FIX нетронут.
- Упаковка prep1: создан ZIP, проверены CRC/хеши, распакован в новую папку. Там новая venv, pinned offline install, pip check, load r6 PASS. Исторические stale links исправлены только в navigation copies (20 копий, 214 разрешённых ссылок, включая 138 ранее сломанных).
- Экспорт: первые попытки удерживали собственный PDF handle, WinError32. Исправлена запись из памяти; failed exports сохранены. Review обнаружил расхождение gate и отсутствие annotations; исправлены новый source/export, активные links. Финальная вёрстка 9 страниц, 83 annotations (9 URI, 74 относительные файлы), 3 legible artifact PNG. Все 9 PNG v3 идентичны просмотренным v2. PDF SHA закреплён в submission-review.md.
- Финальная сборка и проверки точного rc1 выполняются после этих материалов. Их результат/ресурсы сохраняются **вне frozen ZIP**: dist/validation-rc1. Если изменятся packaged bytes, требуется новая версия, а не правка archive evidence задним числом.
