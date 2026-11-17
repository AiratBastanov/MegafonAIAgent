# Одна проверка на независимых открытых данных

**Результат:** существующий агент обработал все 12 330 строк официального набора UCI Online Shoppers Purchasing Intention. Покупкой завершились 1 908 сессий, без покупки — 10 422. В файле 18 колонок: 17 признаков и Revenue; пустых ячеек нет. Структура и числа совпали с [официальным описанием UCI](https://archive.ics.uci.edu/dataset/468/online+shoppers+purchasing+intention+dataset).

Использован файл, заранее скачанный владельцем. Он не скачивался повторно и не менялся. [Атрибуция, фактический путь, лицензия CC BY 4.0 и SHA256](../evaluation/public-data-release/projects/uci-shoppers/inputs/attribution-v1.json). Авторы: C. Sakar и Yomi Kastro, 2018; [DOI набора](https://doi.org/10.24432/C5F88Q). Локальная контрольная сумма подтверждает неизменность нашей копии; официального хеша на прочитанной странице нет.

## Что удалось узнать

| Группа | Покупки / сессии | Доля |
|---|---:|---:|
| Вся выборка | 1 908 / 12 330 | 15,4745% |
| Новые посетители | 422 / 1 694 | 24,9115% |
| Вернувшиеся посетители | 1 470 / 10 551 | 13,9323% |
| Другая категория | 16 / 85 | 18,8235% |

Это собственные расчёты по исходному CSV. Все 23 группы «месяц × тип посетителя» рассчитаны штатной программой и проверены независимым пересчётом оригинала. Исходные строки и ячейки сохранены; добавлены только явные индикаторы для подсчёта. 125 совпадающих наборов признаков не удалялись: без идентификаторов нельзя объявлять их повторными записями людей.

Различие долей — **ассоциация, не эффект продукта**. Revenue обозначает факт покупки, не денежную выручку. Выборка историческая, причины отказа, интерфейс, расходы и применимость к новому магазину неизвестны. Поэтому предложена ограниченная диагностика на современных данных; немедленные скидки и прогноз роста не обоснованы.

## Самостоятельный результат и границы проверки

[Ситуация](../evaluation/public-data-release/projects/uci-shoppers/outputs/v1/situation.md), [четыре варианта](../evaluation/public-data-release/projects/uci-shoppers/outputs/v1/options.md), [продуктовая стратегия](../evaluation/public-data-release/projects/uci-shoppers/outputs/v1/product-strategy.md), [коммуникационная стратегия](../evaluation/public-data-release/projects/uci-shoppers/outputs/v1/communication-strategy.md), [план с контролем, сроками и вредом](../evaluation/public-data-release/projects/uci-shoppers/outputs/v1/validation-plan.md).

Новый результат записан штатным механизмом памяти и загружается отдельным процессом. Анализ и критический проход выполнил координатор этой задачи; это не ещё один независимый LLM-рецензент. Решение остаётся ожидающим владельца. Канонические демонстрации изолированы и не менялись.

Воспроизведение расчёта в новой папке из уже включённого оригинала:

~~~powershell
.\.venv\Scripts\python.exe -X utf8 evaluation/public-data-release/evaluate_uci.py --input evaluation/public-data-release/projects/uci-shoppers/inputs/online_shoppers_intention.csv --project evaluation/public-data-release/reproduced-uci
~~~

[Точный расчёт](../evaluation/public-data-release/projects/uci-shoppers/evidence/calculations/by-month-visitor-v1.json), [независимая арифметика](../evaluation/public-data-release/projects/uci-shoppers/evidence/calculations/independent-v1.json), [карта преобразования](../evaluation/public-data-release/projects/uci-shoppers/inputs/derivation-v1.json), [критическая проверка](../evaluation/public-data-release/projects/uci-shoppers/evidence/review-v1.md).
