"""Write coordinator-authored narrow amendments and prepare a validated state."""
import copy
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path('scripts').resolve()))
import project_state as ps
import decision_followup as df

AS_OF = '2026-12-19T13:00:00+03:00'

TEXTS = {
    'familiar': {
        'phrase': 'recipient needs no account',
        'unknown': 'Необходимость аккаунта получателя неизвестна; отзыв не доказывает, что аккаунт обязателен.',
        'retained': 'Срок семь дней и предел 2 GB на файл этим сообщением не отозваны; они остаются утверждениями описания без производственной приёмки.',
        'product': '''Сохранить исходящую передачу с ручной помощью агентствам как гипотезу для ограниченной проверки. Убрать получение без аккаунта из поддерживаемых обещаний: автор отозвал именно эту часть описания, а фактический порядок доступа неизвестен. До проверки конкретной версии нельзя считать этот способ получения пригодным для предложения. Это не основание объявить обязательный аккаунт, строить авторизацию либо менять сегмент.

Семидневный срок не отозван этим сообщением, но по-прежнему требует приёмки. Экономика при 90 мин поддержки остаётся сценарием; новых затрат или конверсий не подставлять. До приёмки и отдельного решения владельца сохраняется внутренний режим. После приёмки владелец должен оценить, сохранилась ли дополнительная ценность предложения.''',
        'communication': '''Заменить собственное обещание «получателю не нужна учётная запись» в центральном сообщении и сценарий демонстрации «скачивание без аккаунта» на проверку фактического порядка доступа.

Согласованный черновик: «Предлагаем проверить передачу комплекта клиенту по ссылке с ручной помощью команды и сравнить процесс с вашим обычным способом. Порядок доступа получателя подтвердим на проверенной версии до приглашения участников». Это внутренний черновик, не отправленное обещание. Сведения о функции публичного конкурента C004 и другие ограничения продукта не отозваны; их нельзя использовать вместо собственной приёмки.''',
        'validation': '''Перед приглашениями выполнить K-CAPABILITY на конкретной версии и разрешённом файле: открыть внешнюю ссылку в чистой сессии получателя без авторизации; записать, доступны ли получение и скачивание, требуется ли вход/создание аккаунта, какие шаги и ошибки возникают. Сохранить версию, условия, время и результаты проверки; пока результатов нет. В любом случае отдельно проверить размер, истечение и ручной отзыв.

Если безаккаунтный сценарий не подтверждён, не объявлять его действующим и не подменять это выдуманным обязательным аккаунтом. После установленного поведения владелец решает, пригоден ли сценарий для предложения. При изменении доступа учитывать дополнительные шаги/время получателя отдельно от активного времени отправителя; сохранить сопоставимость обычного и тестового способов. Пороги M-TIME/M-FIRST-PAY и scaling-gates не изменены. Семь дней в прежнем календаре остаются условием описания, требующим приёмки; Q2 не вводит другой срок. Фактического старта нет, новые даты не назначены.''',
        'situation': '''Уточнение к «Что известно из материалов»: исторический S001@1 содержит фразу об отсутствии аккаунта получателя, но её текущая поддержка отозвана Q2-WITHDRAWAL@1. Необходимость аккаунта неизвестна. Остальные сообщения S001, синтетическая воронка, сценарная экономика и неизвестные из v2 сохраняются; описание не равно испытанной возможности.''',
        'c001': 'Учебный S001@1 исторически сообщает исходящую ссылку только для скачивания, ручной отзыв, предел 2 GB на файл и семь дней, а входящую загрузку/пароль/именной доступ — как отсутствующие. Это не производственная приёмка. Q2-WITHDRAWAL@1 отозвал поддержку только фразы об отсутствии аккаунта получателя; необходимость аккаунта неизвестна.',
        'c010': 'Ручная помощь в исходящей передаче остаётся гипотезой уменьшения координации агентств сверх обычного инструмента. После отзыва поддержки доступа без аккаунта пригодность текущего сценария и трение для получателя требуют приёмки; дополнительная ценность и готовность платить неизвестны.',
        'proposal': 'Предлагается сохранить внутренний режим и сначала проверить фактический доступ получателя; ограниченную проверку исходящей передачи агентствам обсуждать после приёмки и нового решения владельца о пригодности предложения и бюджете, без обещания доступа без аккаунта.',
        'required_evidence': 'Проверка конкретной версии на разрешённом файле: доступ и скачивание получателем в чистой сессии, необходимость входа/создания аккаунта, шаги и ошибки; также размер, истечение и ручной отзыв. Нужны версия, условия, время и наблюдаемые результаты, а не новый текст описания.',
        'capability_next': 'Получить протокол фактического доступа получателя и остальных возможностей; затем владелец пересматривает пригодность исходящего предложения. До этого исключить обещание доступа без аккаунта.',
        'value_reason': 'Ценность и оплаты неизвестны; неподтверждённый порядок доступа может менять трение получателя и сопоставимость процессов. Эффект этого изменения не измерен.',
    },
    'variant': {
        'phrase': 'links expire after 7 days',
        'unknown': 'Фактический срок ссылки неизвестен; отзыв не доказывает бессрочность, иной срок или отсутствие истечения.',
        'retained': 'Фраза recipient needs no account и предел 2 GB на файл этим сообщением явно не изменены; это прежние утверждения описания, требующие приёмки.',
        'product': '''Сохранить исходящую передачу с ручной помощью агентствам как гипотезу для ограниченной проверки. Убрать семь дней из поддерживаемых условий продукта: фактический срок доступности и поведение автоматического истечения не установлены. До проверки конкретной версии нельзя обещать этот срок или принимать пригодность жизненного цикла ссылки. Ручной отзыв — отдельное заявленное свойство и не заменяет автоматическое истечение.

Получение без аккаунта этим сообщением явно не отозвано; оно остаётся описанием без производственной приёмки. Не объявлять ссылку бессрочной и не назначать новый срок. Экономика при 90 мин поддержки не меняется. Сохраняется внутренний режим до приёмки и решения владельца о пригодности предложения и бюджете.''',
        'communication': '''Заменить «срок ссылки 7 дней» в памятке и любом собственном описании условий на явно неподтверждённый срок. Не обещать автоматическое прекращение доступа через семь дней. Ручной отзыв не выдавать за проверенное автоматическое истечение.

Согласованный черновик: «Предлагаем проверить передачу комплекта клиенту по ссылке с ручной помощью команды и сравнить процесс с вашим обычным способом. Подтверждённый срок доступа и условия отзыва сообщим после проверки конкретной версии». Это внутренний черновик, не отправленное обещание. Фраза об отсутствии аккаунта не отозвана, но использовать её вовне можно только после приёмки; сведения о конкуренте также не заменяют собственную проверку.''',
        'validation': '''Перед приглашениями расширить K-CAPABILITY: на конкретной версии и разрешённом файле зафиксировать настройки срока, время создания ссылки и наблюдаемую доступность/недоступность до и после проверяемой границы. Сохранить протокол времени и поведения автоматического истечения. Ручной отзыв проверять отдельным действием; также проверить доступ, скачивание и размер. Отзыв поддержки не является результатом ни одной из этих проверок.

Прежнюю связку «все передачи до дня 23 → семь суток доставки → завершение к дню 30» нельзя считать выполнимым календарём без подтверждения доступности ссылки. Семь суток в критерии успешной доставки — предлагаемое окно наблюдения, а не установленный срок жизни ссылки: его пригодность нужно проверить; при несовместимости владелец согласует другой критерий и календарь. Новый срок не подставлять. Отдельное окно первой оплаты за 30 суток с фактического дня 0, определения M-TIME и scaling-gates сохраняются как правила обучения. Плановое M-TIME уже истекло, но старт и результаты не сообщались; новых дат нет.''',
        'situation': '''Уточнение к «Что известно из материалов»: S001@1 исторически сообщал срок ссылки семь дней, но Q2-WITHDRAWAL@1 отозвал поддержку этой фразы. Её нельзя использовать как текущее условие возможности; фактический срок неизвестен. Фраза об отсутствии аккаунта получателя и остальные сведения описания не отозваны, но не прошли приёмку. Воронка и сценарная экономика v2 остаются без изменений.''',
        'c001': 'Учебный S001@1 исторически сообщает исходящую ссылку только для скачивания, ручной отзыв, предел 2 GB на файл, семь дней и отсутствие аккаунта получателя; входящая загрузка/пароль/именной доступ указаны как отсутствующие. Q2-WITHDRAWAL@1 отозвал поддержку только семидневного срока; фактический срок неизвестен. Прочие положения не изменены, производственной приёмки нет.',
        'c010': 'Ручная помощь в исходящей передаче остаётся гипотезой уменьшения координации агентств сверх обычного инструмента. После отзыва поддержки семидневного срока пригодность жизненного цикла ссылки для задачи и календаря требует приёмки; дополнительная ценность и готовность платить неизвестны.',
        'proposal': 'Предлагается сохранить внутренний режим и сначала проверить фактический срок и жизненный цикл ссылки; ограниченную проверку исходящей передачи агентствам обсуждать после приёмки и нового решения владельца о пригодности, календаре и бюджете, без обещания семидневного срока.',
        'required_evidence': 'Проверка конкретной версии на разрешённом файле: настройки срока, время создания, наблюдаемая доступность до/после проверяемой границы и автоматическое истечение; отдельно ручной отзыв, доступ/скачивание и размер. Нужны наблюдаемые результаты; новый срок из текста не считается испытанием.',
        'capability_next': 'Получить протокол фактического срока и автоматического истечения отдельно от ручного отзыва; затем согласовать пригодность предложения и календаря с владельцем. До этого исключить обещание семи дней.',
        'value_reason': 'Ценность и оплаты неизвестны; неподтверждённый срок ссылки может менять завершимость передач и календаря. Семь суток наблюдения не доказывают семидневную доступность.',
    },
}


def write_new(path, value, is_json=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n' if is_json else value)


for branch, words in TEXTS.items():
    root = Path('branches') / branch / 'projects/task04-followup'
    baseline = ps.load_state(root)
    data = json.loads((root / 'drafts/q2-evidence-base-v1.json').read_text(encoding='utf-8'))
    assert data['state_sha256'] == baseline['state_sha256'] and baseline['revision'] == 3
    event = json.loads((root / 'inputs/q2/evidence-change-v1.json').read_text(encoding='utf-8'))
    report = json.loads((root / 'notes/q2/raw-impact-v1.json').read_text(encoding='utf-8'))
    assert df.impact(root, data, event) == report
    data, changed = df.apply_event(root, data, event)
    assert changed and data['decision']['reviews'][-1]['owner_review_required'] is True
    review_id = 'review-' + event['id']

    def artifact(relative, aid, value, is_json=False):
        write_new(root / relative, value, is_json)
        data['artifacts'].append(ps.reference(root, relative, aid))

    common_header = ('Синтетическая локальная ветка ' + branch + '; время проверки ' + AS_OF + '. '
                     'Это узкая поправка к соответствующему outputs/v2, не новый принятый бизнес-выбор. '
                     'В затронутой части применяется этот текст; остальное из v2 переиспользуется. '
                     'Реальный запуск, расходы и внешние сообщения не разрешены.\n\n')
    source_footer = ('\n\nОснования: Q2-WITHDRAWAL@1, evidence/sources/Q2-WITHDRAWAL/v1/extract.json, line:1-4; '
                     "S001@1, evidence/sources/S001/v1/extract.json, physical-page:1/block:5 (фраза '" + words['phrase'] + "'), "
                     'и block:4,6-8 для неизменённого контекста. '
                     'C001/C010/C011 уточнены; C015 обозначает отозванную текущую поддержку, C016 — факт сообщения об отзыве. '
                     'Это не новое испытание.\n')
    output_ids = {}
    for name, key, title in (
        ('product-strategy', 'product', 'Поправка продукта'),
        ('communication-strategy', 'communication', 'Поправка сообщения'),
        ('validation-plan', 'validation', 'Поправка плана проверки'),
        ('situation', 'situation', 'Короткое уточнение ситуации'),
    ):
        aid = 'OUTPUT-Q2-' + name
        artifact('outputs/q2/' + name + '-amendment-v1.md', aid,
                 '# ' + title + ' — Q2 v1\n\n' + common_header + words[key] + source_footer)
        output_ids[name] = aid

    source_ref = {'artifact_id': 'Q2-WITHDRAWAL-v1-extract', 'locator': 'line:1-4',
                  'source_id': 'Q2-WITHDRAWAL', 'source_version': 1}
    old_ref = {'artifact_id': 'S001v1-extract', 'locator': 'physical-page:1/block:5',
               'source_id': 'S001', 'source_version': 1}
    claims = {c['id']: c for c in data['claims']}
    for cid in ('C001', 'C010', 'C011'):
        claims[cid].pop('status', None)
        claims[cid].pop('support_reason', None)
    claims['C001']['text'] = words['c001']
    claims['C001']['evidence'].append(copy.deepcopy(source_ref))
    claims['C010']['text'] = words['c010']
    claims['C010']['derived_from'].append('C016')
    claims['C011']['text'] = words['proposal'] + ' Входящий сбор и масштабирование не обоснованы; keep/close остаются альтернативами для владельца.'
    claims['C011']['derived_from'].append('C016')
    # The generic assumption remains valid as written; a propagated flag is not a new fact.
    data['claims'][next(i for i, c in enumerate(data['claims']) if c['id'] == 'C012')] = copy.deepcopy(next(c for c in baseline['claims'] if c['id'] == 'C012'))
    data['claims'].extend([
        {'id': 'C015', 'kind': 'source_fact', 'synthetic': True,
         'text': 'Историческая фраза S001@1 о собственном прототипе: ' + words['phrase'] + '.',
         'status': 'withdrawn',
         'support_reason': 'Текущая поддержка только этой фразы отозвана ' + event['id'] + '. Историческое содержание источника сохраняется. ' + words['unknown'],
         'evidence': [copy.deepcopy(old_ref), copy.deepcopy(source_ref)], 'derived_from': []},
        {'id': 'C016', 'kind': 'source_fact', 'synthetic': True,
         'text': 'Q2-WITHDRAWAL@1 сообщает отзыв поддержки только фразы ' + words['phrase'] + ' из S001@1; нового протокола и результата нет, другие положения и таблица не меняются. ' + words['unknown'],
         'evidence': [copy.deepcopy(source_ref)], 'derived_from': []},
    ])

    before_outputs = copy.deepcopy(baseline['decision']['current_outputs'])
    data['decision']['current_outputs'].update(output_ids)
    replacement_ids = {before_outputs[name]: aid for name, aid in output_ids.items()}
    for condition in data['decision']['conditions']:
        condition['output_ids'] = [replacement_ids.get(aid, aid) for aid in condition['output_ids']]
        if condition['id'] == 'G-CAPABILITY':
            condition['claim_ids'].extend(['C015', 'C016'])
            condition['unresolved_reason'] = 'Отозвана поддержка ' + words['phrase'] + '. ' + words['unknown'] + ' Протокола приёмки нет.'
            condition['next_action'] = words['capability_next']
        elif condition['id'] == 'G-VALUE':
            condition['unresolved_reason'] = words['value_reason']
    capability = next(c for c in data['decision']['commitments'] if c['id'] == 'K-CAPABILITY')
    capability['required_evidence'] = words['required_evidence']
    assert capability['status'] == 'pending'

    dispositions = []
    for affected in report['affected']:
        node = affected['node']
        if node in {'claim:C001', 'claim:C010', 'claim:C011', 'condition:G-CAPABILITY', 'condition:G-VALUE', 'commitment:K-CAPABILITY'}:
            outcome = 'revised'
            reason = 'Уточнены отозванная часть, неизвестность и соответствующее условие приёмки/проверки; нет вывода о противоположном поведении.'
        elif node.startswith('output:') and node[7:] in replacement_ids:
            outcome = 'revised'
            reason = 'Новая узкая поправка ' + replacement_ids[node[7:]] + '; старый файл и hash сохранены.'
        else:
            outcome = 'reviewed_unchanged'
            reason = {
                'claim:C012': 'Правила обучения остаются допущениями; изменение конкретной проверки отражено в новом плане, пороги и размер не переопределяются.',
                'condition:G-ECONOMICS': 'Основания сценарной экономики и потребность в бюджете не менялись; ссылки на обновлённые документы актуализированы.',
                'commitment:K-PROTOCOL': 'Завершение локального документа Q1 остаётся историческим фактом; оно никогда не подтверждало возможности продукта.',
                'commitment:K-BUDGET': 'Остаётся blocked/unassigned с due_at=null; отзыв не согласовывает бюджет и не устраняет зависимость.',
                'commitment:K-VALUE': 'Остаётся blocked/unassigned с due_at=null; реальных наблюдений и разрешения нет.',
                'output:OUTPUT-v2-options': 'Альтернативы из v2 условны на приёмку, бюджет, ценность и экономику; отозванная фраза не является их фактом выбора. Нет основания автоматически сменить сегмент или закрыть направление.',
            }.get(node, 'Проверено по точному смыслу отзыва; изменения текущего содержания не требуется.')
        dispositions.append({'node': node, 'outcome': outcome, 'reason': reason})
    assert len(dispositions) == len(report['affected'])
    reuse = {
        'branch': branch, 'as_of': AS_OF, 'clock': 'simulated',
        'basis_revision': baseline['revision'], 'basis_state_sha256': baseline['state_sha256'],
        'source_id_version': 'S001@1', 'locator': 'physical-page:1/block:5',
        'changed_clause': words['phrase'], 'preserved_clause_note': words['retained'],
        'dispositions': dispositions,
        'reused_artifacts': [a for a in baseline['artifacts'] if a['id'] in {
            'CALC-FUNNEL-v1', 'ECON-RAW-v2', 'ECON-v2', 'ECON-CHECK-v2', 'S002v2-extract',
            'S005v1-extract', 'OUTPUT-v2-options', 'Q1-PROTOCOL'}],
        'reuse_reason': 'XLSX и сценарные значения не изменены, нет новых измерений. Пересчёт не закрывает пробел возможностей. Переиспользование проверено по прежним hash штатным loader.',
        'limitations': 'PDF overlap работает на уровне блоков; различие фраз и скрытая календарная связь установлены координатором. Graph не доказывает фактическое поведение.',
    }
    artifact('notes/q2/impact-disposition-v1.json', 'Q2-IMPACT-DISPOSITION', reuse, True)

    review_text = f'''# Содержательное ревью Q2 — {branch}, v1

База: revision {baseline['revision']} / {baseline['state_sha256']}. Прочитаны новая заметка line:1-4, S001@1 physical-page:1/block:4-8 и пять outputs/v2. Это автоматическая проверка тем же координатором, не независимый агент и не решение владельца.

- Q2-SCOPE, существенное, закрыто: отзыв касается ровно «{words['phrase']}». {words['retained']} Штатный impact возвращает одинаковые 16 узлов для двух фраз одного блока; это карта ссылок, не идентичность продуктовых последствий. Построчное решение по всем узлам — Q2-IMPACT-DISPOSITION.
- Q2-NEGATIVE, существенное, закрыто: {words['unknown']} Новый источник не содержит испытания; факт отзыва C016 отделён от исторического утверждения C015 со статусом withdrawn. C001 сохранён в уточнённой исторической форме, весь S001 не объявлен отозванным.
- Q2-CONSISTENCY, существенное, закрыто: продукт, сообщение и план получили согласованные короткие поправки; ситуация — явное уточнение текущей применимости. Предложение C011 обновлено отдельно от history. Options v2 проверен и переиспользован: его варианты изначально условны на приёмку и бюджет, доказательства автоматической смены сегмента или закрытия нет.
- Q2-PLAN, существенное, закрыто: {words['validation']}
- Q2-ECON, закрыто: S002@2 'Экономика'!E3 остаётся 90 мин, C013/C014 и ECON-v2 не менялись. Ни расходов доступа, ни новой частоты/оплат/продлений не сообщено; исходные сценарии не превращаются в прогноз. Числовой пересчёт не выполнялся. Обоснование reuse и точные hash сохранены.
- Q2-FOLLOWUP, требуется владелец: аналитическая правка может получить revised, но owner_review_required остаётся true. Изменено основание допустимого обещания и условия исходящего предложения. Нужны приёмка и новая инструкция выбора с resolves_reviews; координатор не снимает owner flag. K-CAPABILITY остаётся просроченным; K-BUDGET/K-VALUE заблокированы, ответственные/даты не выдуманы. K-PROTOCOL неизменён.
- Q2-OBSERVATIONS, остаётся неизвестным: M-TIME — окончившийся сценарный план, фактических включений и результатов нет. Остальные окна неизвестны. G-FRESHNESS остаётся открытым требованием проверки перед будущим сравнением. Новые сроки не назначались и внешний эксперимент не разрешён.

Повторная проверка: в текущих поправках нет безусловного собственного обещания отозванной фразы; другой отзыв не перенесён из соседней ветки. История OWNER-01, исходные inputs/outputs и q1.md сохранены. Структурный validator отдельно проверяет ссылки, hash, события и переход; он не испытывает продукт. Проверки реального поведения и человеческое решение не выполнены.
'''
    artifact('notes/q2/review-v1.md', 'Q2-CONTENT-REVIEW', review_text)
    resolution_event = {
        'id': 'Q2-' + branch.upper() + '-REVIEW', 'project_id': 'task04-followup',
        'kind': 'review', 'at': AS_OF, 'clock': 'simulated', 'review_id': review_id,
        'provenance': {'kind': 'agent_review', 'artifact_id': 'Q2-CONTENT-REVIEW', 'locator': 'Q2-SCOPE — Q2-OBSERVATIONS'},
        'resolution': {
            'status': 'revised', 'owner_review_required': True,
            'reason': 'Частичный отзыв учтён в текущих claims и коротких поправках; остальные элементы явно reviewed_unchanged. Фактическая возможность неизвестна; исходное решение требует владельческого пересмотра.',
            'next_action': words['capability_next'] + ' Для закрытия owner review нужна отдельная инструкция выбора с resolves_reviews=[' + review_id + '].',
            'resolution_evidence': [
                {'artifact_id': 'Q2-CONTENT-REVIEW', 'locator': 'Q2-SCOPE — Q2-OBSERVATIONS'},
                {'artifact_id': 'Q2-IMPACT-DISPOSITION', 'locator': 'dispositions; reused_artifacts'},
                *[{'artifact_id': aid, 'locator': 'основной текст поправки'} for aid in output_ids.values()],
            ],
            'proposed_option': words['proposal'],
        }
    }
    artifact('inputs/q2/review-resolution-v1.json', 'Q2-REVIEW-EVENT', resolution_event, True)
    data, changed = df.apply_event(root, data, resolution_event)
    assert changed
    data['stage'] = 'awaiting_decision'
    data['completed'].append('Q2: частичный отзыв ' + words['phrase'] + ' зарегистрирован; аналитическая правка revised, решение владельца остаётся открытым.')
    data['next_action'] = resolution_event['resolution']['next_action']
    data['pending_actions'] = [
        words['capability_next'],
        'Владельцу пересмотреть предложение с учётом ' + words['phrase'] + '; отдельный choice должен ссылаться на ' + review_id + '. Приёмка и аналитическое revised не снимают owner_review_required.',
        'Назначить ответственного за бюджет и отдельно согласовать пределы затрат и новый календарь; K-BUDGET/K-VALUE остаются blocked/unassigned.',
        'Получить фактические даты включения и наблюдения, если они существуют; не трактовать истечение планового M-TIME как результат.',
        'Перед будущим использованием альтернатив проверить актуальность S003/S004; ранее наступившее G-FRESHNESS не снято.',
    ]
    data['unresolved_questions'].append(words['unknown'] + ' Нужен протокол конкретной версии; текст отзыва его не заменяет.')
    assert data['decision']['history'] == baseline['decision']['history']
    assert data['decision']['status'] == baseline['decision']['status'] == 'simulated_accepted'
    assert data['decision']['metrics'] == baseline['decision']['metrics']
    assert next(c for c in data['decision']['commitments'] if c['id'] == 'K-PROTOCOL') == next(c for c in baseline['decision']['commitments'] if c['id'] == 'K-PROTOCOL')
    for cid in ('C007', 'C008', 'C013', 'C014'):
        assert next(c for c in data['claims'] if c['id'] == cid) == next(c for c in baseline['claims'] if c['id'] == cid)

    handoff = f'''# Передача контекста Q2 — {branch}, v1

На {AS_OF}, clock=simulated. Основание: revision 3 / {baseline['state_sha256']}; после публикации authoritative current проверять load, не по существованию draft. Прежний OWNER-01-decision и его grounds сохранены, status=simulated_accepted относится только к прежней подготовке. Новое предложение ожидает владельца.

Событие {event['id']}: withdrawn_support из S001@1, physical-page:1/block:5, только «{words['phrase']}». Происхождение source_material; Q2-WITHDRAWAL@1 line:1-4, не инструкция выбора. {words['unknown']} {words['retained']}

Аналитическое событие {resolution_event['id']} даёт review {review_id} статус revised, owner_review_required=true. Его нельзя закрыть повтором старого OWNER-01 или агентским review. Требуется новая инструкция выбора с resolves_reviews=[{review_id}], закреплённая к загруженной опубликованной revision. При прерывании сначала reconcile по двум ID событий.

Текущие product/communication/validation/situation — короткие поправки outputs/q2/*-amendment-v1.md поверх соответствующих v2. Options v2 reviewed_unchanged. Все 16 узлов разобраны в notes/q2/impact-disposition-v1.json; различие фраз в одном PDF-блоке и зависимость календаря проверены вручную. Старые файлы не перезаписаны.

Ближайший шаг: {words['capability_next']} K-CAPABILITY остаётся pending/overdue, уточнено требуемое evidence. K-BUDGET/K-VALUE blocked/unassigned с неизвестными датами; K-PROTOCOL уже выполнен и не изменён. Приёмка не подтверждена. Никаких новых владельцев/дат/расходов/приглашений не назначено.

Экономика и воронка неизменны: S002@2 E3=90, C007/C008/C013/C014, ECON-v2 и источники сохраняют прежние hash; повторного импорта и пересчёта нет. M-TIME остаётся окончившимся планом без сообщённого старта/результатов; фактические окна других метрик неизвестны. G-FRESHNESS не закрыт. Реальный эксперимент не разрешён.

Следующий ввод: протокол конкретной версии и новая инструкция уполномоченного владельца; до них сужать обещания по поправкам и сохранять внутренний режим. Полный первый ответ q1 неизменён; первый ответ q2 и метаданные сохраняются в package-root/responses/q2.md и q2-meta.json.
'''
    artifact('notes/q2/handoff-v1.md', 'Q2-HANDOFF', handoff)
    ps.validate_state(root, data)
    df.validate_transition(baseline, data)
    write_new(root / 'drafts/q2-followup-v1.json', data, True)
    with (root / 'state/actions.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps({
            'at': datetime.now(timezone.utc).isoformat(), 'action': 'Q2 prepare and review narrow withdrawal amendment',
            'clock': 'simulated', 'as_of': AS_OF, 'input_revision': 3, 'event_id': event['id'],
            'review_event_id': resolution_event['id'], 'outcome': 'candidate_validated_not_published',
            'owner_review_required': True, 'new_choice': False, 'errors': [], 'retries': 0,
            'model': None, 'tokens': None, 'charges': None,
        }, ensure_ascii=False) + '\n')
    print(json.dumps({'branch': branch, 'draft': 'drafts/q2-followup-v1.json', 'validated': True,
                      'review_id': review_id, 'review_status': 'revised', 'owner_review_required': True,
                      'history_preserved': True, 'q1_completion_preserved': True,
                      'current_outputs': data['decision']['current_outputs'],
                      'publication': 'pending'}, ensure_ascii=False, indent=2))
