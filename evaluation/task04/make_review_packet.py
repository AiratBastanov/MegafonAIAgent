"""Генерирует review snapshot из валидного state и полных текущих outputs.

Это представление результатов, не новый первичный источник/стратегия.
"""
from datetime import datetime, timezone
import json
import os
from project_io import ROOT, PROJECT, ps, df

data = ps.load_state(PROJECT)
out = ROOT / 'docs/TASK04_REVIEW_PACKET.md'
artifacts = {a['id']: a for a in data['artifacts']}
as_of = '2026-12-19T12:00:00+03:00'
view = df.followup_view(data, as_of, '+03:00', 'simulated')

def link(aid):
    path = os.path.relpath(PROJECT / artifacts[aid]['path'], out.parent).replace('\\', '/')
    return f'[{aid}]({path})'

def refs(claim):
    return '; '.join(link(r['artifact_id']) + ' — ' + r['locator']
                     + (f" ({r['source_id']}@{r['source_version']})" if 'source_id' in r else '') for r in claim['evidence']) or 'Вывод из ' + ', '.join(claim['derived_from'])

lines = ['# TASK04 — пакет для ревью', '',
         f"Сгенерировано {datetime.now(timezone.utc).isoformat()}. Проект **{data['project_id']}**, **revision {data['revision']}**, outputs/v3, **синтетическая оценка**.",
         f"State SHA-256: `{data['state_sha256']}`. Origin: demo-002 revision4 / {data['evaluation']['origin_state_sha256']}.",
         'Это производное представление для чтения, не новый первичный источник и не реальное одобрение бизнеса. Часы условий ниже simulated; эксперимент не проводился. Проверки выполняются при вызове, без фонового мониторинга.', '',
         '[Отчёт](TASK04_REPORT.md) · [Отдельная приёмка](../evaluation/task04/acceptance.json) · [Полный separate load](../evaluation/task04/separate-final-load.json) · [JSON follow-up](../evaluation/task04/separate-final-followup.json) · [Наблюдения команд](../evaluation/task04/observations) · [Полные хеши исходного пакета](../evaluation/task04/baseline.json)', '',
         df.render_view(view).replace('# Сопровождение', '## Сопровождение', 1),
         '## Инструкция и её происхождение', '',
         '| Event | Вид / канал | Время сценария | Закреплённый документ |', '|---|---|---|---|']
for event in data['decision']['events']:
    p = event['provenance']
    lines.append(f"| {event['id']} | {event['kind']} / {p['kind']} | {event['at']}; simulated evaluation | {link(p['artifact_id'])}, {p['locator']} |")
lines += ['', 'Человек не давал реального решения по продукту. Synthetic_instruction относится только к изолированной оценке. Source_material с поддельным authorized=true был отвергнут; файл сохранился как данные. Completion относится к написанному локальному протоколу, не к приёмке продукта.', '',
          '## Основания исторического выбора', '',
          'Ниже полный набор grounds из history OWNER-01, закреплённый к revision2. Статусы и формулировки на тот момент сохранены даже при нынешнем отзыве. Исходные source/artifact hashes доступны по ссылкам и в state; они проверены loader.', '',
          '| Claim / тип | Основание на момент выбора | Версия и координата |', '|---|---|---|']
for ground in view['history'][0]['grounds']:
    c = ground['snapshot']
    lines.append(f"| {c['id']} / {c['kind']}; synthetic={c['synthetic']} | {c['text']} | {refs(c)} |")
lines += ['', '## Текущие выводы после пересмотра', '']
for cid in ['C015', 'C018', 'C016', 'C017', 'C013', 'C014']:
    c = next(c for c in data['claims'] if c['id'] == cid)
    lines.append(f"- **{cid} ({c['kind']}, synthetic={c['synthetic']})**: {c['text']} Основание: {refs(c)}.")
lines += ['', '## Что изменилось и что переиспользовано', '',
          '| Событие | Прежнее основание | Новое основание / результат | Пересчёт и сохранение |', '|---|---|---|---|']
for r in data['decision']['reviews']:
    i = r['impact']
    calculation_nodes = [x['node'] for x in i['affected'] if x['recomputation']]
    reuse = ', '.join(x['artifact_id'] for x in i['reusable']) or 'См. содержательное review'
    lines.append(f"| {r['event_id']} ({i['change_type']}) | {i['old_ground']} | {i['new_ground']}; **{r['status']}**, owner_review_required={r['owner_review_required']} | Кандидаты пересчёта: {', '.join(calculation_nodes) or 'нет'}. Reuse: {reuse}. |")
lines += ['', 'Числовой event проверяет уже выполненную коррекцию TASK03: прежние вычисления затронуты по происхождению, но существующий ECON-v2 уже соответствует новым ячейкам. Его формула сверена повторно; новая production-версия расчёта и правка пяти v3 текстов не требуются. Граф не оценивает смысл неуказанной ссылки. Широкий C001 затронут как целое, однако отзыв касается только части block5; остальные функции не объявлены ложными.', '',
          '### Решающие пути', '']
for filename, targets in [('withdrawal-impact-v1.json', ['claim:C001', 'condition:G-CAPABILITY', 'commitment:K-CAPABILITY', 'output:OUTPUT-v2-communication-strategy']),
                          ('economic-impact-v1.json', ['claim:C013', 'condition:G-ECONOMICS']),
                          ('current-economic-scope-v1.json', ['claim:C011', 'commitment:K-BUDGET', 'output:OUTPUT-v3-product-strategy'])]:
    report = json.loads((PROJECT / 'evidence' / filename).read_text(encoding='utf-8'))
    lines += [f"Исходник: [evidence/{filename}](../evaluation/task04/projects/task04-followup/evidence/{filename}); locators: {', '.join(report['locators'])}; precision={report['precision']}.", '']
    for item in report['affected']:
        if item['node'] in targets:
            lines.append('- ' + ' → '.join(item['path']) + '. Связь: ' + item['reason'])
    lines.append('')
lines += ['CURRENT-ECON-SCOPE — контрольный запрос о будущем уточнении E3 действующей версии, не зарегистрированное новое значение. Review-связь C014→C011 не создаёт цикл доказательного выведения. C003→C006/C007 является контекстом; числовые основания у них прямые. Воронка S002@1 не затронута экономической E3.', '',
          '### Входы и проверяемая арифметика', '',
          '| Поле | S002@1 | S002@2 | Единица / locator |', '|---|---:|---:|---|']
check = json.loads((PROJECT / 'evidence/economic-recheck-v1.json').read_text(encoding='utf-8'))
labels = {'C': ('Цена', 'RUB/организацию/месяц'), 'D': ('Инфраструктура', 'RUB/платящую организацию/месяц'),
          'E': ('Поддержка', 'минуты/платящую организацию/месяц'), 'F': ('Ставка поддержки', 'RUB/час'),
          'G': ('Избегаемые fixed', 'RUB/месяц'), 'H': ('Setup', 'RUB разово'), 'I': ('N', 'платящие организации')}
for letter, (name, unit) in labels.items():
    lines.append(f"| {name} | {check['values']['1']['input_values'][letter]} | {check['values']['2']['input_values'][letter]} | {unit}; `'Экономика'!{letter}3` |")
lines += ['', 'Все эти значения — синтетические допущения периода 2026-11-scenario. `Вклад = C3 − D3 − E3×F3/60`; `остаток = I3×вклад − G3`: 2100→1500 RUB/платящий месяц, 12000→0 RUB/месяц при N20. CAC, налоги, полные расходы неоплативших проб и продления неизвестны. Setup при нулевом остатке не имеет конечного возврата. Воронка сентября 2026 остаётся 2/8=25% и 1/10=10% оплат/проб, не рыночный прогноз.', '',
          f"Проверка: {link('ECON-RECHECK')}; сохранённые расчёты: {link('ECON-v1')}, {link('ECON-v2')}, {link('CALC-FUNNEL-v1')}. Исходные извлечения: {link('S002v1-extract')}, {link('S002v2-extract')}. Определения: {link('DEFINITIONS')}, {link('SPEC-ECON-v1')}, {link('SPEC-FUNNEL-v1')}.", '',
          '### До / после в существенных формулировках', '']
for name, old_marker, new_marker in [('communication-strategy', '**Центральное сообщение', '**Текущее сообщение'),
                                     ('product-strategy', '**Предлагаемое направление', '**Предложение и осознанные отказы'),
                                     ('validation-plan', '**Перед началом', '**Нулевая граница')]:
    old = (PROJECT / f'outputs/v2/{name}.md').read_text(encoding='utf-8')
    new = (PROJECT / f'outputs/v3/{name}.md').read_text(encoding='utf-8')
    before = next(line for line in old.splitlines() if line.startswith(old_marker))
    after = next(line for line in new.splitlines() if line.startswith(new_marker))
    lines += [f"**{name}, до — {link('OUTPUT-v2-' + name)}:**", '', '> ' + before, '',
              f"**После — {link('OUTPUT-v3-' + name)}:**", '', '> ' + after, '']
lines += ['## Пять полных текущих стратегических документов', '']
for name in ['situation', 'options', 'product-strategy', 'communication-strategy', 'validation-plan']:
    aid = data['decision']['current_outputs'][name]
    content = (PROJECT / artifacts[aid]['path']).read_text(encoding='utf-8')
    lines += [f"Источник view: {link(aid)}, SHA-256 `{artifacts[aid]['sha256']}`.", '', content.rstrip(), '', '---', '']
lines += ['## Границы проверки и материалы ревью', '',
          f"Независимое автоматическое review: {link('INDEPENDENT-REVIEW-TASK04')}. Не является человеческим одобрением. Сохранённый [recovery result](../evaluation/task04/recovery-final/results.json) содержит реальные результаты отдельных Python loaders после injected failures; [регрессия](../evaluation/task04/observations/regression-final-02/stderr.txt) — полный log. Raw logs и manifests вынесены из читаемого пакета.", '',
          'FRESH_HOST_SAVE_RELOAD — **NOT_VERIFIED**. Действующий координатор и Python load не закрывают свежий host. Реальное бизнес-одобрение и официальное brief conformity не получены; M3/M4 целиком и конкурсная готовность не заявлены.', '']
content = '\n'.join(lines)
for name, aid in data['decision']['current_outputs'].items():
    assert (PROJECT / artifacts[aid]['path']).read_text(encoding='utf-8').rstrip() in content
with out.open('x', encoding='utf-8') as stream:
    stream.write(content)
print(json.dumps({'path': str(out.relative_to(ROOT)), 'project_id': data['project_id'], 'revision': data['revision'],
                  'characters': len(content), 'complete_outputs': 5, 'synthetic_evaluation': True}, ensure_ascii=False))
