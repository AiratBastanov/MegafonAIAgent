# Закреплённые пакеты для установки без сети

Три неизменённых wheel взяты из существующего локального кэша установочных пакетов pip. Проверены Name/Version и хеши всех записей wheel RECORD; полные SHA-256 и размеры — в PROVENANCE.json. Кэшированные HTTP-заголовки и учётные данные не читались. Исходная `.venv` не копировалась.

Пакеты: openpyxl 3.1.5, pypdf 7.1.0, et-xmlfile 2.0.0. Лицензии и notices сохранены внутри исходных `.dist-info` в wheels. Это объявленные runtime dependencies; export-tools сюда не добавлены.

Источник публичных сведений о версиях: [openpyxl](https://pypi.org/project/openpyxl/3.1.5/), [pypdf](https://pypi.org/project/pypdf/7.1.0/), [et-xmlfile](https://pypi.org/project/et-xmlfile/2.0.0/), чтение 16.11.2026. Независимое сравнение SHA с PyPI не заявляется: web-представление страницы не выдало искомые хеши. Включённые байты и внутренние RECORD проверены локально.

Из корня распаковки: `.\.venv\Scripts\python.exe -m pip install --no-index --find-links third_party/wheels -r requirements.txt`.
