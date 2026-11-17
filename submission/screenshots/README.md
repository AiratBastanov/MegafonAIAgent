# Изображения фактических файлов

Эти PNG — рендеры исходного PDF, аналитического Markdown и сохранённого stdout. Интерфейс Codex не имитировался. Они показывают артефакты/вывод команды, но не живую независимую сессию. Просмотрены на читаемость; полные изображения доступны без масштаба страницы отчёта.

| PNG | Реальный источник | Наблюдение с SHA/методом |
|---|---|---|
| [source-brief-p02.png](source-brief-p02.png) | [S001 PDF, физическая страница 2](../../projects/task06-rehearsal/inputs/product-brief-v1.pdf) | [render-source](../../evaluation/task06/observations/render-source/stdout.txt) |
| [result-v2-fixed-p01.png](result-v2-fixed-p01.png) | [Ситуация v2](../../projects/task06-rehearsal/outputs/v2/situation.md) | [render-result-fixed](../../evaluation/task06/observations/render-result-fixed/stdout.txt) |
| [followup-r6-fixed-p01.png](followup-r6-fixed-p01.png) | [Подлинный stdout](../../evaluation/task06/observations/followup-final/stdout.txt), его побайтная копия [followup-r6.md](followup-r6.md) | [render-followup-fixed](../../evaluation/task06/observations/render-followup-fixed/stdout.txt) |

Renderer: Markdown 3.9 / PyMuPDF 1.26.3, scale 1.6. Первые неудачные PDF exports сохранены в `evaluation/task06/export-failed-01`; ссылка жюри ведёт на исправленные файлы. Отдельные PDF [ситуации](result-v2-fixed.pdf) и [follow-up](followup-r6-fixed.pdf) тоже читаемы.
