"""Mechanical preparation of the coordinator-authored Q1 records; no publication."""
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path('scripts').resolve()))
import project_state as ps
import decision_followup as df
import import_materials as importer

AS_OF = '2026-12-19T12:00:00+03:00'
NOW = datetime.now(timezone.utc).isoformat()
BRANCHES = ('familiar', 'variant')


def write_new(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(text)


def write_json(path, value):
    write_new(path, json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def normalized_decision(data):
    value = copy.deepcopy(data['decision'])
    for item in value['history']:
        item['basis']['state_sha256'] = 'branch-specific valid basis hash'
    return value


states = {b: ps.load_state(Path('branches') / b / 'projects/task04-followup') for b in BRANCHES}
assert normalized_decision(states['familiar']) == normalized_decision(states['variant'])
assert states['familiar']['claims'] == states['variant']['claims']
assert states['familiar']['artifacts'] == states['variant']['artifacts']
print('Business records match; only the historical basis hash differs between decisions.')

protocol = '''# Локальный протокол Q1 — версия 1

1. Границы и статус. Это синтетическая локальная симуляция task04-followup. Реальный эксперимент, расходы, приглашения, внешние обещания и сообщения не разрешены. OWNER-01 — simulated_accepted подготовки проверки; реального бизнес-решения нет. Сценарные часы этой проверки: 2026-12-19T12:00:00+03:00. Сохраняется внутренний режим. Источник: inputs/owner-instruction-v1.md, абзацы 2–6; decision.history[OWNER-01-decision].

2. До любого внешнего действия нужны приёмка конкретной версии на разрешённом файле (доступ, скачивание, истечение и отзыв), согласованные правила данных и явное решение уполномоченного владельца о пределах затрат. K-CAPABILITY остаётся pending; K-BUDGET и K-VALUE заблокированы. Подготовка этого текста завершает только K-PROTOCOL. Источник: decision.commitments[K-PROTOCOL,K-CAPABILITY,K-BUDGET,K-VALUE], исходная revision 2; outputs/v2/validation-plan.md, «Перед началом».

3. Learning gate — только правила обучения, не полученный эффект. Предложено 10 организаций, по две сопоставимые передачи каждым способом; порядок способов фиксируется. M-TIME: разность медиан активного времени обычного и тестового способов внутри организации; минимум 5 минут у минимум 7 из всех 10 включённых. Пропуски не превращаются в успех; время команды отдельно. M-FIRST-PAY: реальные поступления 3000 RUB за 30 суток с одинакового предложения дня 0; минимум 3 из всех 10 с полным окном. Интерес и счёт не платёж. Успешность доставки сравнивается с обычным способом; разбор сбоев обязателен. Источник: decision.metrics[M-TIME,M-FIRST-PAY]; outputs/v2/validation-plan.md, таблица метрик и «Гипотеза и сравнение».

4. Scaling gate требует частоты задач, ценности клиенту, повторных платежей и полной фактической экономики: M-FREQUENCY/M-VALUE/M-RENEWAL/M-COST. Пять минут сами по себе не обосновывают цену. Учитываются все пробы, включая неоплативших, время команды, инфраструктура, CAC/onboarding, налоги, fixed/setup и обязательства; пересекающиеся представления не складываются. Полный оплаченный месяц и продление имеют отдельные окна. При нуле оплат стоимость на платящего неопределённа. Неизвестные расходы не равны нулю. Источник: decision.metrics; C008/C012/C013; outputs/v2/product-strategy.md, «Выручка и затраты»; outputs/v2/validation-plan.md, таблица и «Решение».

5. Календарь и неопределённость. Окно M-TIME 18 ноября — 18 декабря 2026 года было сценарным планом. На 19 декабря оно закончилось по календарю; включение организаций и старт не сообщались, результаты не получены. Это не завершённый пилот и не провал измеренного эффекта. Новые даты не назначены. До нового этапа нужно получить приёмку, назначить ответственного, согласовать бюджет и календарь с владельцем. При неполных наблюдениях исход — неопределённо; при подтверждённом инциденте применяются остановка и разбор из outputs/v2/validation-plan.md, «Нежелательные последствия». Реальный запуск остаётся запрещён в рамках этой симуляции.

Проверка координатора: пункты 1–5 содержат learning/scaling, неизвестные и запрет реального запуска; это полностью соответствует required_evidence K-PROTOCOL. Сам текст не подтверждает K-CAPABILITY, бюджет или результаты. Независимый reviewer и человеческое одобрение не привлекались.
'''

for branch in BRANCHES:
    root = Path('branches') / branch / 'projects/task04-followup'
    baseline = states[branch]
    data = copy.deepcopy(baseline)
    incoming = Path('inbox/q1/repeated-correction-v1.txt').read_bytes()
    target = root / 'inputs/q1/repeated-correction-v1.txt'
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(incoming)
    imported = importer.register(
        root, 'Q1-REPEAT', 'inputs/q1/repeated-correction-v1.txt', 'text',
        origin='supplied inbox/q1/repeated-correction-v1.txt; synthetic repetition of S005@1',
        synthetic=True, locator='line:1-3',
        limitations=['Повтор сообщения; не новая версия S005 или XLSX, не новое независимое измерение.'],
    )
    assert not imported['reused'] and imported['source']['version'] == 1
    refs = []
    for aid, name in [('Q1-REPEAT-v1-meta', 'source.json'),
                      ('Q1-REPEAT-v1-original', 'original.txt'),
                      ('Q1-REPEAT-v1-extract', 'extract.json')]:
        data['artifacts'].append(ps.reference(root, 'evidence/sources/Q1-REPEAT/v1/' + name, aid))
        refs.append(aid)
    data['sources'].append({'id': 'Q1-REPEAT', 'version': 1, 'synthetic': True, 'artifact_ids': refs})

    def artifact(relative, aid, value, is_json=False):
        (write_json if is_json else write_new)(root / relative, value)
        data['artifacts'].append(ps.reference(root, relative, aid))

    extract = json.loads((root / 'evidence/sources/S002/v2/extract.json').read_text(encoding='utf-8'))
    cells = [c for s in extract['sheets'] for c in s['cells'] if c['locator'] == "'Экономика'!E3"]
    assert len(cells) == 1 and cells[0]['value'] == 90
    duplicate_event = {
        'id': 'Q1-REPEAT-IMPACT-ONLY', 'project_id': 'task04-followup',
        'kind': 'evidence_change', 'at': AS_OF,
        'provenance': {'kind': 'source_material', 'artifact_id': 'Q1-REPEAT-v1-extract', 'locator': 'line:1-3'},
        'change': {
            'type': 'nonmaterial', 'source': {'id': 'S005', 'version': 1},
            'locators': ['line:1-5'],
            'reason': 'Повторно прислана уже учтённая коррекция; новых значений, файла XLSX или измерений нет.',
            'old_ground': 'S005@1 уже учтён в S002@2: Экономика!E3 = 90 минут.',
            'new_ground': 'То же основание: Экономика!E3 = 90 минут.',
            'applicability': 'Применим как повтор сообщения; не меняет C014/C013/C011, расчёты или выбор OWNER-01.'
        }
    }
    artifact('inputs/q1/repeat-impact-assessment-v1.json', 'Q1-REPEAT-ASSESSMENT', duplicate_event, True)
    ps.validate_state(root, data)
    impact = df.impact(root, data, duplicate_event)
    artifact('notes/q1/repeated-message-impact-v1.json', 'Q1-RAW-IMPACT', impact, True)

    view_before = df.followup_view(baseline, AS_OF, '+03:00', 'simulated')
    stamp = datetime.fromisoformat(AS_OF)
    chronology = {
        'as_of': AS_OF, 'clock': 'simulated',
        'basis_revision': baseline['revision'], 'basis_state_sha256': baseline['state_sha256'],
        'deadline_elapsed_days': {
            c['id']: (stamp - datetime.fromisoformat(c['due_at'])).total_seconds() / 86400
            for c in baseline['decision']['commitments'] if c['due_at'] is not None
        },
        'M-TIME': {
            'window': baseline['decision']['metrics'][0]['window'],
            'days_since_planned_end': (stamp - datetime.fromisoformat(baseline['decision']['metrics'][0]['window']['end'])).total_seconds() / 86400,
            'interpretation': 'Плановое окно закончилось; фактический старт и результаты неизвестны.'
        },
        'commitments_before': view_before['commitments'],
        'G-FRESHNESS': next(c for c in view_before['conditions'] if c['id'] == 'G-FRESHNESS')
    }
    artifact('notes/q1/chronology-v1.json', 'Q1-CHRONOLOGY', chronology, True)
    artifact('notes/q1/local-protocol-v1.md', 'Q1-PROTOCOL', protocol)

    audit = f'''# Проверка повтора и ограничений — Q1 v1

Проверка координатора, не независимое доказательство. Ветка {branch}; база revision {baseline['revision']}, state_sha256 {baseline['state_sha256']}. Все новые материалы синтетические; фактических наблюдений нет.

- Q1-DUP (закрыто): входящее Q1-REPEAT@1, line:1-3, прямо называет повтор S005@1 без новой XLSX/величин/измерений. S005@1, line:1-5, уже вводит 90 минут; проверена S002@2, 'Экономика'!E3 = 90. C014/C013 и ECON-v2 учитывают коррекцию. Это не новая версия прежнего источника и не основание пересчитывать модель. Входящая квитанция зарегистрирована отдельно; S005/S002 не импортировались заново.
- Q1-TOOL (ограничение, учтено): штатный impact для type=nonmaterial по тем же координатам возвращает {len(impact['affected'])} затронутых узлов, precision={impact['precision']}. Он обходит совпадающие ссылки и не устанавливает новизну содержания. Применение такого повторного сообщения как нового evidence_change создало бы лишний review и owner_review_required. Поэтому impact сохранён как диагностический расчёт; событие Q1-REPEAT-IMPACT-ONLY не применено. Это отсутствие изменения, а не снятие существующего review: reviews исходно пуст. Реализация утилиты не изменялась.
- Q1-DATES (закрыто): дата проверки минус 17 ноября = 32 суток для K-PROTOCOL/K-CAPABILITY; дата минус конец M-TIME = 1 сутки. Время сценарное, не системное. K-PROTOCOL закрывается только после записи/проверки отдельного протокола; K-CAPABILITY остаётся просроченным. Даты K-BUDGET/K-VALUE неизвестны — просрочку им не приписываем. Расчёт: Q1-CHRONOLOGY.
- Q1-RESULTS (остаётся пробелом данных): запрос и context.md сообщают отсутствие старта/результатов; decision.metrics[M-TIME].window — план. ended_evidence_required в view требует проверить evidence, но не означает состоявшийся эксперимент. M-FIRST-PAY и scaling-метрики не имеют фактических окон и результатов. Нельзя подставлять нули, успех либо провал.
- Q1-REUSE (закрыто): хеши всех исходных артефактов обеих веток проверены штатным load; пять outputs/v2 прочитаны и согласованы с локальным протоколом. C009/C002 остаются исторически superseded. C013/C014, ECON-v2 и outputs/v2 сохранены без новых версий и без пересчёта, потому что входы не изменены. decision.history и choice OWNER-01 не изменяются.
- Q1-OWNER (открыто для владельца): повтор коррекции не требует нового стратегического выбора. Отсутствие необходимых наблюдений и невыполненные предпосылки требуют решения о дальнейшем подготовительном этапе, ответственных, бюджете и новом календаре (OWNER-INSTRUCTION, абзацы 4–6). Приёмка должна предшествовать внешним обещаниям; реальных разрешений/решений здесь нет.
- Q1-FRESH (пробел перед будущим сравнением): G-FRESHNESS.review_after=2026-12-01T12:00:00+03:00 уже наступил. S003/S004 — старые сохранённые снимки. Актуальность перед новым сравнением не проверена; дата сама по себе их не опровергает. Live web запрещён рамками этого задания и для текущего вывода не нужен.

Структура и ссылки кандидата проверяются штатным validator; это не доказательство работы прототипа. Содержательное автоматическое ревью выполнено этим же координатором. Независимого агента, внешнего сервиса и человеческого решения не было.
'''
    artifact('notes/q1/review-and-reuse-v1.md', 'Q1-REVIEW-AND-REUSE', audit)

    event = {
        'id': 'Q1-K-PROTOCOL-COMPLETE', 'project_id': 'task04-followup',
        'kind': 'completion', 'at': AS_OF, 'clock': 'simulated',
        'provenance': {'kind': 'agent_review', 'artifact_id': 'Q1-REVIEW-AND-REUSE', 'locator': 'Q1-DATES; заключительный абзац'},
        'commitment_id': 'K-PROTOCOL',
        'completion_evidence': [{'artifact_id': 'Q1-PROTOCOL', 'locator': 'пункты 1–5 и проверка координатора'}],
        'completion_check': 'Сохранён и прочитан локальный протокол: learning/scaling, неизвестные, запрет реального запуска. Завершена только подготовка документа; нет подтверждения приёмки, бюджета, старта или результатов.'
    }
    artifact('inputs/q1/protocol-completion-v1.json', 'Q1-PROTOCOL-COMPLETION', event, True)
    data, changed = df.apply_event(root, data, event)
    assert changed
    assert data['decision']['history'] == baseline['decision']['history']
    assert data['decision']['reviews'] == baseline['decision']['reviews'] == []
    assert data['claims'] == baseline['claims']
    assert data['decision']['metrics'] == baseline['decision']['metrics']
    data['completed'].append('Q1: проверен повтор S005@1 без нового изменения; локальный K-PROTOCOL выполнен с доказательством, остальные результаты не заявлены.')
    data['next_action'] = 'Владельцу получить приёмку конкретной версии, назначить ответственного за бюджет и решить, продолжать ли подготовку с новым согласованным календарём; до этого внутренний режим.'
    data['pending_actions'] = [
        'Получить требуемый K-CAPABILITY протокол: версия, разрешённый файл, доступ/скачивание/истечение/отзыв; срок 17 ноября 2026 сценарно просрочен.',
        'Назначить владельца K-BUDGET и отдельно решить цену информации и календарь; не считать бюджет согласованным.',
        'Уточнить фактический старт/включения/наблюдения; при их отсутствии M-TIME остаётся завершившимся планом, все результаты неизвестны.',
        'Перед будущим сравнением актуализировать S003/S004 разрешённым способом; G-FRESHNESS наступило 1 декабря.',
        'Не выполнять K-VALUE до разблокировки и отдельного реального разрешения; собрать частоту/ценность/продления/полные расходы только с фактическими окнами.'
    ]
    handoff = f'''# Передача контекста — Q1, {branch}, версия 1

Проверка на {AS_OF}, +03:00, clock=simulated. База: revision {baseline['revision']}, state_sha256 {baseline['state_sha256']}. После публикации authoritative запись — state/current.json; revision базы не выдаётся за результат публикации. Обе ветки имеют одинаковые бизнес-факты; история закреплена разными hash своих баз.

Сохраняется OWNER-01: simulated_accepted только подготовки исходящего предложения; реального одобрения нет. Стадия awaiting_decision. Нового choice не было.

Повтор inbox/q1 зарегистрирован как Q1-REPEAT@1 (line:1-3), а не как S005@2/S002@3. S005@1 уже учтён в S002@2, 'Экономика'!E3=90; C014/C013, ECON-v2 и пять outputs/v2 переиспользованы. Новых расчётов, требований владельцу из повтора и review нет. Детали ограничения impact: notes/q1/review-and-reuse-v1.md, Q1-TOOL; diagnostic event не применять автоматически.

K-PROTOCOL: подготовлен notes/q1/local-protocol-v1.md; завершение Q1-K-PROTOCOL-COMPLETE публикуется штатным save. При возобновлении проверить load и reconcile по этому ID, а не повторять запись. Срок 17 ноября пропущен на 32 сценарных суток, документ создан при текущей проверке. Это не приёмка и не запуск.

K-CAPABILITY остаётся pending и просроченным на 32 суток. K-BUDGET blocked/unassigned вследствие K-CAPABILITY, K-VALUE blocked/unassigned вследствие K-BUDGET; due_at у обоих null, просрочка неизвестна. Никого и новых сроков не назначали.

План M-TIME 18 ноября — 18 декабря истёк сутки назад. Запуск/включения и результаты не сообщались; эксперимент нельзя считать состоявшимся, успешным либо проваленным. У M-FIRST-PAY и четырёх scaling-метрик окна неизвестны. Нужны фактические даты и evidence. G-FRESHNESS наступило 1 декабря; перед новым сравнением проверить S003/S004, актуальность пока неизвестна.

Следующий шаг владельца: получить протокол приёмки конкретной версии; назначить ответственного за цену информации; отдельно решить продолжение подготовки, бюджет и новый календарь. Условие возврата к решению из OWNER-INSTRUCTION, абзац 6, сработало из-за отсутствия необходимых наблюдений; повтор коррекции не причина для нового выбора. Сохранение внутреннего режима — текущая граница, а не разрешение эксперимента. Практическое действие с внешними людьми не выполнялось.

Не импортировать неизменённые входы заново и не завершать предметные обязательства без требуемого evidence. Новое настоящее изменение обрабатывать отдельным impact/review с новыми версиями и сохранением истории. Логи текущего вызова находятся в package-root/logs/q1-*; первичная записка и метаданные — package-root/responses/q1.md и q1-meta.json.
'''
    artifact('notes/q1/handoff-v1.md', 'Q1-HANDOFF', handoff)
    ps.validate_state(root, data)
    df.validate_transition(baseline, data)
    artifact('notes/q1/view-before-publication-v1.json', 'Q1-CANDIDATE-VIEW', {
        'publication_status': 'candidate_only; based_on_revision_2',
        'view': df.followup_view(data, AS_OF, '+03:00', 'simulated')
    }, True)
    ps.validate_state(root, data)
    write_json(root / 'drafts/q1-followup-v1.json', data)
    action = {
        'at': NOW, 'action': 'Q1 prepare followup candidate', 'as_of': AS_OF,
        'clock': 'simulated', 'input_revision': baseline['revision'],
        'outcome': 'candidate_validated_not_published',
        'artifacts': ['Q1-PROTOCOL', 'Q1-HANDOFF', 'Q1-REVIEW-AND-REUSE', 'Q1-RAW-IMPACT'],
        'sources': ['S005@1', 'S002@2', 'Q1-REPEAT@1'],
        'errors': [], 'retries': 0, 'external_help': [],
        'model': None, 'tokens': None, 'charges': None,
        'resource_note': 'Не предоставлены; точные subprocess времена — package-root/logs/q1-*.'
    }
    with (root / 'state/actions.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(action, ensure_ascii=False) + '\n')
    print(json.dumps({
        'branch': branch, 'draft': 'drafts/q1-followup-v1.json', 'validated': True,
        'impact_affected_nodes': len(impact['affected']), 'impact_applied': False,
        'duplicate_requires_new_choice': False,
        'completion_event': event['id'], 'publication': 'pending',
        'overdue_days_before_completion': chronology['deadline_elapsed_days'],
        'days_since_planned_window_end': chronology['M-TIME']['days_since_planned_end']
    }, ensure_ascii=False))
