# Локальные инструменты

Техническая числовая граница: ≤18 цифр коэффициента, модуль десятичного exponent ≤12. Суммы и финальное округление не теряют промежуточную точность.

Запускает агент из корня. На Windows `python` в примерах можно заменить на `.\.venv\Scripts\python.exe`. Утилиты не обращаются к моделям/сети и не выбирают стратегию.

```powershell
python scripts/import_materials.py --project projects/demo-001 --source-id S001 --input inputs/brief-v1.docx --kind docx --synthetic
python scripts/import_materials.py --project projects/demo-001 --source-id S002 --input inputs/cohorts-v1.csv --kind csv --synthetic
python scripts/analyze_table.py --project projects/demo-001 --input inputs/cohorts-v1.csv --spec inputs/metrics-total.json --source-id S002 --source-version 1 --output evidence/calculations/total-v1.json
python scripts/project_state.py load --project projects/demo-001
```

Для web-excerpt дополнительно обязательны `--origin URL --accessed-at ISO --locator SECTION --retrieval-status current_host_read` либо `supplied_snapshot`. `--limitations` можно повторять. Этот инструмент регистрирует уже прочитанную выдержку; сама команда не доказывает чтение сайта. Для реальных собственных данных не ставь synthetic; для учебных ставь всегда.

Spec CSV задаёт точные `columns` с type (text/integer/decimal), unit, необязательными min/max; `group_by` обязательно включает `period_column`, `missing_values`, `synthetic`; `metrics` с id/operation(sum|ratio)/numerator/[denominator]/unit/rounding/multiplier. Примеры в demo inputs. Для retained ≤ eligible используй `constraints:[{"operation":"lte","left":"retained_d28","right":"eligible"}]`.

Сумма требует одинаковых единиц; отношение с multiplier=100 одинаковых единиц выдаёт %. Пропуск значимого слагаемого даёт null/status=missing, нулевой знаменатель — null. Периоды не смешиваются автоматически. ROUND_HALF_UP, 0–10 десятичных знаков. Результат содержит определения, числитель/знаменатель, locator строк, spec/input hash и synthetic. Существующий output не перезаписывается.

CLI возвращает JSON и ненулевой exit при ошибке. Прочитай ошибку и исправь вход/выбери другой маршрут; не объявляй шаг завершённым. Технические safeguards: файл 20 MiB, распакованный DOCX 80 MiB, CSV 50 000 строк; доступны соответствующие `--max-*`. Это защита парсера, не квота исследования и не измеренная производительность на предельном размере. Количество источников/действий/проходов не ограничено этим контрактом.
