"""Создаёт только синтетические входы; не стратегии и не трассу агента."""
import argparse
import csv
import json
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZipFile, ZIP_DEFLATED


def paragraph(text):
    return '<w:p><w:r><w:t>' + escape(text) + '</w:t></w:r></w:p>'


def make_docx(path, blocks):
    body = []
    for block in blocks:
        if isinstance(block, str):
            body.append(paragraph(block))
        else:
            body.append('<w:tbl>' + ''.join('<w:tr>' + ''.join('<w:tc>' + paragraph(c) + '</w:tc>' for c in row) + '</w:tr>' for row in block) + '</w:tbl>')
    with ZipFile(path, 'x', compression=ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr('_rels/.rels', '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr('word/document.xml', '<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>' + ''.join(body) + '<w:sectPr/></w:body></w:document>')


def generate(project):
    inputs = project / 'inputs'
    inputs.mkdir(parents=True, exist_ok=True)
    make_docx(inputs / 'brief-v1.docx', [
        'УЧЕБНЫЙ СИНТЕТИЧЕСКИЙ ПРИМЕР. Не официальный дополнительный бриф МегаФона.',
        'Продукт «Ритм»: личный веб-планировщик для небольших регулярных дел. Руководитель: «Повторное использование падает. Нам исправить первый опыт, вложиться в регулярные задачи или вообще свернуть направление?»',
        [['Статус', 'Возможности'], ['Сейчас', 'Ручное создание задачи, дата, список, отметка выполнения, ручное копирование задачи.'], ['Предлагается', 'Обучающий первый сценарий и автоматические повторяющиеся задачи. Ни то ни другое пока не реализовано.']],
        'Аудитория обозначает при регистрации recurring (регулярные дела) или occasional (разовые задачи). Это самоотчёт, не наблюдение частоты поведения. Источник привлечения не сохранён; в сентябре изменились рекламные объявления.',
        'CSV содержит две когорты регистрации: август и сентябрь 2026, обе наблюдались 28 дней полностью. eligible — зарегистрированные уникальные пользователи; activated — создали первую задачу за 24 часа; retained_d28 — выполнили хотя бы одну задачу на днях 22–28; paid — оплатили первый месяц; revenue_rub — полученная выручка первого месяца. Платящие могут не быть retained_d28. Цена: 300 рублей за месяц, возвраты не моделировались.',
        'Менеджер считает, что люди не понимают первый экран. Интервью, рандомизированного теста и пользовательских логов для проверки этого объяснения нет.',
        'Неизвестны избегаемые ежемесячные фиксированные расходы направления и переменные затраты на платящего. Стоимость разработки и обслуживания новых функций тоже не оценена. Необходимо показать сценарии и пороги, а не объявлять прибыль.',
        'Разрешены чтение этих синтетических файлов и официальной публичной справки сопоставимого сервиса. Реальных клиентов, персональных данных и закрытых сведений нет. Решение о расходах/закрытии принимает руководитель; его согласие пока не получено.'
    ])
    rows = [
        ['2026-08', 'recurring', 400, 320, 240, 80, 24000, ''],
        ['2026-08', 'occasional', 100, 50, 20, 5, 1500, ''],
        ['2026-09', 'recurring', 100, 80, 60, 20, 6000, ''],
        ['2026-09', 'occasional', 400, 200, 80, 20, 6000, ''],
    ]
    columns = ['period', 'segment', 'eligible', 'activated', 'retained_d28', 'paid', 'revenue_rub', 'variable_cost_rub']
    with (inputs / 'cohorts-v1.csv').open('x', encoding='utf-8', newline='') as f:
        w = csv.writer(f); w.writerow(columns); w.writerows(rows)
    spec = {
        'group_by': ['period', 'segment'], 'period_column': 'period', 'synthetic': True,
        'missing_values': ['', 'NA'],
        'columns': {c: {'type': 'text', 'unit': u} for c, u in [('period', 'registration_month'), ('segment', 'self_reported_category')]},
        'metrics': [], 'constraints': []
    }
    for c in columns[2:]:
        spec['columns'][c] = {'type': 'integer', 'unit': 'RUB' if c.endswith('_rub') else 'users', 'min': '0'}
    for metric, numerator in [('activation_pct', 'activated'), ('retention_pct', 'retained_d28'), ('paid_pct', 'paid')]:
        spec['metrics'].append({'id': metric, 'operation': 'ratio', 'numerator': [numerator], 'denominator': ['eligible'], 'multiplier': '100', 'unit': '%', 'rounding': 2})
        spec['constraints'].append({'operation': 'lte', 'left': numerator, 'right': 'eligible'})
    for metric, numerator in [('revenue_rub', 'revenue_rub'), ('variable_cost_rub', 'variable_cost_rub')]:
        spec['metrics'].append({'id': metric, 'operation': 'sum', 'numerator': [numerator], 'unit': 'RUB', 'rounding': 2})
    for name, groups in [('metrics-segments.json', ['period', 'segment']), ('metrics-total.json', ['period'])]:
        spec['group_by'] = groups
        (inputs / name).write_text(json.dumps(spec, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (inputs / 'DATA_DICTIONARY.md').write_text('''# Синтетические данные

Все строки созданы разработчиком для проверки агента; они не описывают рынок.
CSV UTF-8, разделитель запятая. period — месяц регистрации; D28 измерен на днях 22–28, не день оплаты. Все когорты дозрели.
eligible, activated, retained_d28, paid — пользователи, целые числа ≥0. Каждое из трёх подмножеств ≤ eligible; вложенность paid в retained не предполагается.
revenue_rub — RUB за первый месяц когорты, не MRR всей базы и не прибыль. variable_cost_rub — общие переменные расходы этой когорты за первый месяц; пустое значение означает неизвестно, не 0.
Суммирование разных когорт допустимо только как сумма первых месяцев, не как выручка одного календарного месяца. Проценты: сумма числителей / сумма eligible ×100; ROUND_HALF_UP до 2 знаков. Нулевой знаменатель — неопределённо.
Сегмент — выбор пользователя при регистрации. Изменение рекламы создаёт конкурирующее объяснение, данных по каналу нет.
''', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--project', type=Path, required=True)
    generate(parser.parse_args().project.resolve())
