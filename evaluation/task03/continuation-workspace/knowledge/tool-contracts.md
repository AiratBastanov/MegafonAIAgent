# Локальные инструменты M1/M2

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

## XLSX и текстовый PDF

Среда: Python 3.12; `python -m venv .venv`, затем `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`. Версии закреплены: openpyxl 3.1.5, pypdf 7.1.0, et-xmlfile 2.0.0. Существующую Windows `.venv` не копировать на другой хост: создать заново либо явно указать проверенный interpreter.

```powershell
python scripts/import_materials.py --project projects/example-002 --source-id S001 --input inputs/brief.pdf --kind pdf --synthetic
python scripts/import_materials.py --project projects/example-002 --source-id S002 --input inputs/data.xlsx --kind xlsx --selection inputs/selection.json --synthetic
```

Для XLSX обязателен файл выбора, например `{"ranges":[{"sheet":"Лист 1","range":"A1:D8","units":{"A":"month","B":"category","C":"accounts","D":"accounts"},"period":"2026-09"}]}`. Имя листа сохраняется буквально, конечные диапазоны не пересекаются. Период и единицы — явные определения координатора по словарю источника, неизвестное — `null`; формат ячейки сам их не удостоверяет. Извлечение сохраняет значения/типы/формат числа/дату, пустые ячейки, скрытые листы/строки/колонки, объединения и anchor, комментарии и текст ссылок. Значение объединённой ячейки не размножается; для вычисления таких данных нужен однозначный исходный экспорт.

Формула хранится отдельно от кэша. `data_only` не пересчитывает книгу. `cache_status=missing/error/present`, свежесть всегда `unknown`; даже присутствующий кэш не становится проверенной метрикой. Макросы, вложения, внешние связи и array/data-table formulas в выбранных ячейках отклоняются. Формулы, hyperlinks и команды из содержимого не исполняются. Содержание картинок/диаграмм не извлекается; наличие таких частей отражено в ограничениях. Это поддержка выбранных ячеек, не произвольного Excel-документа.

`analyze_table.py` принимает тот же оригинал XLSX как `--input`, обязательные source ID/version и обычный spec с дополнением:

```json
{"xlsx":{"sheet":"Лист 1","rows":[3,4],"columns":{"period":"A","segment":"B","eligible":"C","paid":"D"},"include_hidden":false}}
```

Остальные `columns/group_by/period_column/metrics/missing_values/synthetic` нужны как для CSV. Все выбранные колонки и строки перечислены явно; `missing_values` включает `""`. Единицы числовых колонок должны совпасть с import selection, значение period-ячейки — с selection.period. Формулы, ошибки, merged cells, даты/boolean в числовом поле отклоняются. Скрытые ячейки требуют осознанного `include_hidden=true`. Нормализация существует только в памяти; результат содержит карту каждого поля к исходной ячейке, хеш оригинала/извлечения/spec, source type/method/limitations. Missing сохраняет исходную координату и даёт null; синтетика наследуется. Пример команды: `python scripts/analyze_table.py --project projects/example-002 --input inputs/data.xlsx --spec inputs/metrics.json --source-id S002 --source-version 1 --output evidence/calculations/funnel-v1.json`.

PDF: поддержан простой неповёрнутый текстовый слой. Locator `physical-page:2/block:4` означает физическую страницу (с 1) и фрагмент visitor в порядке извлечения; это не доказанный визуальный абзац. `page_label` — PDF metadata/default, отдельно от напечатанного номера, который при необходимости сверяют с оригиналом. Пустая/сканированная страница, шифрование, формы, сломанные символы и явный поворот дают ошибку с предложением текстового экспорта. Колонки/табличные полосы, XObject и annotations получают `needs_layout_review`; такие места нельзя молча превращать в таблицу или проверенное основание. Присутствие текста не доказывает полноту: решающие фразы/числа сверяет координатор с оригиналом, сохраняя метод проверки. OCR, визуальный рендер и произвольные PDF-таблицы не заявляются.

Дополнительные настраиваемые guards: `--max-cells 100000` (stored и selected), `--max-sheets 64`, `--max-pages 200`, `--max-page-stream 8388608`, `--max-text-chars 2000000`; XLSX использует также `--max-unpacked 83886080`. PDF stream проверяется после распаковки pypdf: это не абсолютный лимит памяти для враждебного сжатого файла. Для больших/неподдерживаемых материалов нужен меньший автономный экспорт и сохранённая карта происхождения, а не молчаливая потеря содержимого.
