"""Сопровождение решений при вызове. Проверяет связи, не выбирает стратегию.

Авторитетная запись — decision в опубликованном state. Markdown/JSON view
производны. Один писатель; источники не могут подтвердить решение человека.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
import sys


class FollowupError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise FollowupError(message)


def text_value(value, name):
    require(isinstance(value, str) and bool(value.strip()), f"Нужно непустое поле {name}")


def moment(value):
    text_value(value, 'time')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        require(result.utcoffset() is not None, 'Нужно явное смещение часового пояса')
        return result
    except ValueError as exc:
        raise FollowupError('Нужно время ISO 8601 с часовым поясом') from exc


def unique(items, label):
    require(isinstance(items, list), f'{label}: нужен список')
    result = {}
    for item in items:
        require(isinstance(item, dict), f'{label}: нужна запись')
        key = item.get('id')
        require(isinstance(key, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.@-]{0,127}', key),
                f'{label}: неверный ID')
        require(key not in result, f'{label}: повтор ID')
        result[key] = item
    return result


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def check_ref(ref, artifacts):
    require(isinstance(ref, dict) and ref.get('artifact_id') in artifacts,
            'Ссылка требует существующий закреплённый artifact_id')
    text_value(ref.get('locator'), 'locator')


def acyclic(edges, label):
    visiting, done = set(), set()
    def visit(node):
        require(node not in visiting, f'Цикл {label}')
        if node in done:
            return
        visiting.add(node)
        for child in edges.get(node, []):
            visit(child)
        visiting.remove(node)
        done.add(node)
    for node in edges:
        visit(node)


def validate_extensions(data, read_artifact, read_basis):
    """Вызывается state validator после проверки файлов, evidence и derived_from."""
    artifacts = {a['id']: a for a in data['artifacts']}
    claims = {c['id']: c for c in data['claims']}
    sources = {(s['id'], s['version']): s for s in data['sources']}
    for claim in claims.values():
        for field in ('review_dependencies', 'context_from'):
            refs = claim.get(field, [])
            require(isinstance(refs, list) and all(isinstance(x, str) and x in claims for x in refs),
                    f'{field}: неизвестный claim')
        require(not (set(claim.get('context_from', [])) & set(claim['derived_from'])),
                'Одна связь не может быть одновременно контекстной и доказательной')
    deps = data.get('artifact_dependencies', [])
    require(isinstance(deps, list), 'artifact_dependencies: нужен список')
    edges = {}
    for dep in deps:
        require(isinstance(dep, dict) and dep.get('from') in artifacts and dep.get('to') in artifacts,
                'Неизвестный artifact dependency')
        text_value(dep.get('reason'), 'dependency.reason')
        edges.setdefault(dep['from'], []).append(dep['to'])
    acyclic(edges, 'вычислительных артефактов')
    decision = data['decision']
    if 'format_version' not in decision:
        return  # Старые schema1 ревизии доступны без миграции.
    require(decision['format_version'] == 2, 'Неизвестный decision.format_version')
    for field in ('question', 'proposed_option', 'owner'):
        text_value(decision.get(field), f'decision.{field}')
    events = unique(decision.get('events'), 'events')
    history = unique(decision.get('history'), 'history')
    commitments = unique(decision.get('commitments'), 'commitments')
    metrics = unique(decision.get('metrics'), 'metrics')
    conditions = unique(decision.get('conditions'), 'conditions')
    reviews = unique(decision.get('reviews'), 'reviews')
    for aid in decision.get('current_outputs', {}).values():
        require(aid in artifacts, 'Неизвестный текущий output')
    for event in events.values():
        require(event.get('project_id') == data['project_id'], 'Событие относится к другому проекту')
        moment(event.get('at'))
        require(event.get('kind') in {'choice', 'evidence_change', 'completion', 'review'}, 'Неизвестный вид события')
        provenance = event.get('provenance', {})
        require(provenance.get('kind') in {'user_instruction', 'synthetic_instruction', 'source_material', 'agent_review'},
                'Неизвестное происхождение события')
        check_ref(provenance, artifacts)
        require(event.get('fingerprint') == digest({k: v for k, v in event.items() if k != 'fingerprint'}),
                'Fingerprint события не совпадает')
        if event['kind'] == 'evidence_change':
            validate_change(data, event['change'])
    used_instruction_events = set()
    for record in history.values():
        for field in ('question', 'option', 'reason', 'owner'):
            text_value(record.get(field), f'history.{field}')
        require(record.get('status') in {'accepted', 'rejected', 'simulated_accepted'}, 'Неверный статус выбора')
        event = events.get(record.get('instruction_event'))
        require(event is not None and event['kind'] == 'choice', 'Выбор требует отдельное событие инструкции')
        require(record['instruction_event'] not in used_instruction_events, 'Одно событие не создаёт два решения')
        used_instruction_events.add(record['instruction_event'])
        choice = event.get('choice', {})
        require(all(record.get(k) == choice.get(k) for k in ('question', 'option', 'reason', 'owner', 'rejected_alternatives')),
                'История выбора должна соответствовать инструкции')
        channel = event['provenance']['kind']
        if record['status'] == 'simulated_accepted':
            require(data.get('evaluation', {}).get('synthetic') is True and channel == 'synthetic_instruction',
                    'Симуляция разрешена только явно синтетическому evaluation-проекту')
            require(choice.get('status', 'accepted') == 'accepted', 'Симуляция принятия не может подменять отказ')
        else:
            require(channel == 'user_instruction' and event.get('authorized') is True,
                    'Документ/ответ tool/рекомендация не являются подтверждением пользователя')
            text_value(event.get('actor'), 'actor')
            require(record['status'] == choice.get('status', 'accepted'), 'Статус истории не соответствует выбору пользователя')
        alternatives = record.get('rejected_alternatives')
        require(isinstance(alternatives, list) and len(alternatives) >= 1, 'Нужны осмысленные отвергнутые альтернативы')
        for alt in alternatives:
            text_value(alt.get('option'), 'alternative.option')
            text_value(alt.get('reason'), 'alternative.reason')
        basis = record.get('basis', {})
        require(type(basis.get('revision')) is int and basis['revision'] > 0
                and isinstance(basis.get('state_sha256'), str)
                and re.fullmatch('[a-f0-9]{64}', basis['state_sha256']), 'Нужна закреплённая исходная revision')
        require(isinstance(record.get('grounds'), list) and record['grounds'], 'Выбор требует основания')
        original = read_basis(basis['revision'])
        require(original['state_sha256'] == basis['state_sha256'], 'Не совпадает исходная revision решения')
        original_claims = {c['id']: c for c in original['claims']}
        original_artifacts = {a['id']: a for a in original['artifacts']}
        original_sources = {(s['id'], s['version']): s for s in original['sources']}
        require([g['claim_id'] for g in record['grounds']] == choice.get('ground_ids'), 'Основания не соответствуют инструкции')
        for ground in record['grounds']:
            require(ground.get('claim_id') in claims, 'Неизвестное основание решения')
            # Полный снимок текста/evidence/версий не меняется при коррекции текущих claims.
            snapshot = ground.get('snapshot')
            require(isinstance(snapshot, dict) and snapshot.get('id') == ground['claim_id'], 'Нужен снимок основания')
            require(original_claims.get(ground['claim_id']) == snapshot, 'Снимок основания не совпадает с исходной revision')
            for ref in snapshot.get('evidence', []):
                check_ref(ref, artifacts)
                require(artifacts[ref['artifact_id']] == original_artifacts.get(ref['artifact_id']),
                        'Нельзя переназначить artifact исторического основания')
                if 'source_id' in ref:
                    key = (ref['source_id'], ref.get('source_version'))
                    require(key in sources and sources[key] == original_sources.get(key), 'Неверная версия исторического основания')
            text_value(snapshot.get('text'), 'snapshot.text')
    if history:
        latest = list(history.values())[-1]
        require(decision['status'] == latest['status'], 'Текущий статус должен следовать последнему выбору, не review')
        if latest['status'] in {'accepted', 'rejected'}:
            instruction = events[latest['instruction_event']]
            confirmation = decision.get('human_confirmation', {})
            require(confirmation.get('actor') == instruction['actor'] and confirmation.get('at') == instruction['at']
                    and confirmation.get('evidence_artifact_id') == instruction['provenance']['artifact_id'],
                    'Подтверждение должно относиться к последней инструкции выбора')
    else:
        require(decision['status'] in {'proposed', 'awaiting_decision'}, 'Принятый выбор требует историю')
    block_edges = {}
    for item in commitments.values():
        require(item.get('decision_id') in history, 'Обязательство требует решение из истории')
        for field in ('description', 'owner', 'due_condition', 'required_evidence'):
            text_value(item.get(field), f'commitment.{field}')
        require(item.get('status') in {'pending', 'blocked', 'completed', 'cancelled'}, 'Неверный статус обязательства')
        require('due_at' in item, 'Неизвестный срок задаётся due_at=null')
        if item.get('due_at') is not None:
            moment(item['due_at'])
        refs = item.get('blocked_by', [])
        require(isinstance(refs, list) and all(x in commitments for x in refs), 'Неизвестная блокирующая зависимость')
        block_edges[item['id']] = refs
        require(all(x in conditions for x in item.get('condition_ids', [])), 'Неизвестное условие обязательства')
        for ref in item.get('completion_evidence', []):
            check_ref(ref, artifacts)
        if item['status'] == 'completed':
            require(bool(item.get('completion_evidence')), 'Завершение требует доказательство')
            event = events.get(item.get('completion_event'))
            require(event is not None and event['kind'] == 'completion', 'Нужно событие проверки завершения')
            text_value(item.get('completion_check'), 'Почему evidence удовлетворяет определению завершения')
            require(event['provenance']['kind'] in {'agent_review', 'user_instruction', 'synthetic_instruction'},
                    'Источник не может сам объявить обязательство выполненным')
            require(event.get('commitment_id') == item['id'] and event.get('completion_evidence') == item['completion_evidence']
                    and event.get('completion_check') == item['completion_check'], 'Завершение не соответствует событию проверки')
            require(all(commitments[x]['status'] == 'completed' for x in refs), 'Завершение заблокировано зависимостью')
    acyclic(block_edges, 'блокирующих обязательств')
    for metric in metrics.values():
        for field in ('definition', 'unit', 'denominator', 'observation_period', 'needed_evidence'):
            text_value(metric.get(field), f'metric.{field}')
        require(metric.get('gate') in {'learning', 'scaling'}, 'Разделите learning/scaling gates')
        for field in ('comparator', 'threshold'):
            require(field in metric, f'Нужно явное {field}, допустимо null')
        window = metric.get('window')
        if window is not None:
            require(moment(window['end']) > moment(window['start']), 'Неверное окно наблюдения')
            require(window.get('clock') in {'actual', 'simulated'}, 'Нужен clock наблюдения')
    for condition in conditions.values():
        for field in ('description', 'next_action'):
            text_value(condition.get(field), f'condition.{field}')
        for field, registry in [('claim_ids', claims), ('metric_ids', metrics), ('output_ids', artifacts)]:
            require(isinstance(condition.get(field), list) and all(x in registry for x in condition[field]),
                    f'condition.{field}: неизвестная ссылка')
        if condition.get('review_after') is not None:
            moment(condition['review_after'])
    for review in reviews.values():
        require(review.get('event_id') in events, 'Пересмотр требует событие')
        require(review.get('status') in {'needs_review', 'revised', 'reviewed_unchanged'}, 'Неверный результат review')
        for field in ('reason', 'next_action'):
            text_value(review.get(field), f'review.{field}')
        require(type(review.get('owner_review_required')) is bool, 'Нужно отделить review агента от решения владельца')
        for ref in review.get('resolution_evidence', []):
            check_ref(ref, artifacts)
        if review['status'] != 'needs_review':
            require(bool(review.get('resolution_evidence')), 'Закрытие review требует доказательства проверки')
            resolution = events.get(review.get('resolution_event'))
            require(resolution is not None and resolution['kind'] == 'review' and resolution.get('review_id') == review['id'],
                    'Закрытие review требует отдельное событие проверки')
            require(all(review.get(k) == resolution['resolution'].get(k) for k in ('status', 'reason', 'next_action', 'resolution_evidence')),
                    'Результат review не соответствует событию')
        require(review.get('impact', {}).get('event_id') == review['event_id'], 'Нужна цепочка impact соответствующего события')
        valid_nodes = ({'claim:' + x for x in claims} | {'artifact:' + x for x in artifacts}
                       | {'output:' + x for x in artifacts} | {'condition:' + x for x in conditions}
                       | {'commitment:' + x for x in commitments}
                       | {f'source:{sid}@{version}' for sid, version in sources})
        for item in review['impact'].get('affected', []):
            require(item.get('node') in valid_nodes and all(n in valid_nodes for n in item.get('path', [])),
                    'Неизвестный узел пути impact')
    for event in events.values():
        if event['kind'] == 'choice':
            require(event['id'] in used_instruction_events, 'Неполное событие choice: нет результата выбора')
        elif event['kind'] == 'evidence_change':
            require(sum(r['event_id'] == event['id'] for r in reviews.values()) == 1,
                    'Неполное событие evidence_change: нужен один результат impact/review')
        elif event['kind'] == 'completion':
            require(sum(c.get('completion_event') == event['id'] for c in commitments.values()) == 1,
                    'Неполное событие completion: нет подтверждённого обязательства')
        else:
            require(event.get('review_id') in reviews, 'Неполное событие review: неизвестный результат')
            require(event['provenance']['kind'] == 'agent_review', 'Документ не является аналитическим review агента')
            resolution = event.get('resolution')
            require(isinstance(resolution, dict) and resolution.get('status') in {'needs_review', 'revised', 'reviewed_unchanged'},
                    'Неполное событие review: нет результата проверки')
            for field in ('reason', 'next_action'):
                text_value(resolution.get(field), 'resolution.' + field)
            require(type(resolution.get('owner_review_required')) is bool, 'Нужен owner_review_required в событии review')
            require(isinstance(resolution.get('resolution_evidence'), list), 'Нужен список resolution_evidence')
            if resolution['status'] != 'needs_review':
                require(bool(resolution['resolution_evidence']), 'Закрытие review требует доказательство в событии')
            for ref in resolution['resolution_evidence']:
                check_ref(ref, artifacts)
            later = [e for e in list(events.values())[list(events).index(event['id']) + 1:]
                     if e['kind'] == 'review' and e.get('review_id') == event['review_id']]
            if not later:
                current_review = reviews[event['review_id']]
                require(current_review.get('resolution_event') == event['id']
                        and all(current_review.get(k) == resolution[k] for k in ('status', 'reason', 'next_action', 'resolution_evidence')),
                        'Последний review event не применён к результату')


def validate_transition(previous, candidate):
    """Опубликованные события/выборы append-only; review не переписывает человека."""
    old, new = previous['decision'], candidate['decision']
    if new.get('status') in {'accepted', 'rejected'} and new != old:
        require(new.get('format_version') == 2, 'Новое бизнес-решение требует format_version=2 и provenance инструкции')
    if old.get('format_version') != 2:
        return
    require(new.get('format_version') == 2, 'Нельзя удалить сопровождение из новой revision')
    for field in ('history', 'events'):
        require(new[field][:len(old[field])] == old[field], f'История {field} неизменяема; добавьте новое событие')
    for record in new['history'][len(old['history']):]:
        require(record['basis'] == {'revision': previous['revision'], 'state_sha256': previous['state_sha256']},
                'Новый выбор закрепляется к загруженной опубликованной revision, не orphan history')
    new_artifacts = {a['id']: a for a in candidate['artifacts']}
    require(all(new_artifacts.get(a['id']) == a for a in previous['artifacts']),
            'Сохраните прежние artifact ID/path/hash; новые байты получают новый ID')
    new_events = new['events'][len(old['events']):]
    for review in old['reviews']:
        matching = next((x for x in new['reviews'] if x['id'] == review['id']), None)
        require(matching is not None, 'Нельзя удалить требование пересмотра')
        require(matching['impact'] == review['impact'] and matching['event_id'] == review['event_id'],
                'Историческая цепочка impact неизменяема')
        if review['owner_review_required'] and not matching['owner_review_required']:
            require(any(e['kind'] == 'choice' and review['id'] in e.get('resolves_reviews', []) for e in new_events),
                    'Требование решения владельца снимается только новой инструкцией выбора')
    for item in old['commitments']:
        matching = next((x for x in new['commitments'] if x['id'] == item['id']), None)
        require(matching is not None, 'Обязательство нельзя удалить; явно отмените с причиной')
        if item['status'] == 'completed':
            require(matching == item, 'Завершённое обязательство сохраняется; коррекция отдельной записью')


CHANGE_TYPES = {'corrected_value', 'superseding_version', 'withdrawn_support', 'new_contradiction',
                'changed_assumption', 'freshness_review', 'nonmaterial'}


def validate_change(data, change):
    require(isinstance(change, dict) and change.get('type') in CHANGE_TYPES, 'Неизвестный вид изменения')
    sources = {(s['id'], s['version']) for s in data['sources']}
    for field in ('source', 'replacement'):
        source = change.get(field)
        if field == 'source' or source is not None:
            require(isinstance(source, dict) and type(source.get('version')) is int
                    and (source.get('id'), source['version']) in sources, 'Изменение требует существующую source/version')
    for field in ('reason', 'old_ground', 'new_ground', 'applicability'):
        text_value(change.get(field), f'change.{field}')
    require(isinstance(change.get('locators'), list) and change['locators']
            and all(isinstance(x, str) and x for x in change['locators']), 'Нужны изменённые координаты либо *')


def artifact_json(project, data, aid):
    # Вызывается только после validate_state: пути и хеши уже проверены.
    item = next(a for a in data['artifacts'] if a['id'] == aid)
    if Path(item['path']).suffix.lower() != '.json':
        return None
    try:
        value = json.loads((Path(project) / item['path']).read_text(encoding='utf-8-sig'))
        return value if isinstance(value, dict) else None
    except (UnicodeError, json.JSONDecodeError):
        return None


def xlsx_extract(project, data, source):
    entry = next(s for s in data['sources'] if s['id'] == source['id'] and s['version'] == source['version'])
    for aid in entry['artifact_ids']:
        extracted = artifact_json(project, data, aid)
        if extracted and extracted.get('format') == 'xlsx':
            return extracted
    return None


def compare_selection(project, data, old, new):
    old_extract, new_extract = xlsx_extract(project, data, old), xlsx_extract(project, data, new)
    if old_extract is None or new_extract is None:
        return None
    def cells(extracted):
        return {cell['locator']: cell for sheet in extracted['sheets'] for cell in sheet['cells']}
    def scope(extracted):
        return {'selection': extracted.get('selection'),
                'sheets': [{k: v for k, v in sheet.items() if k != 'cells'} for sheet in extracted['sheets']]}
    a, b = cells(old_extract), cells(new_extract)
    changes = [{'locator': loc, 'old': a.get(loc), 'new': b.get(loc)}
               for loc in sorted(a.keys() | b.keys()) if a.get(loc) != b.get(loc)]
    return {'method': 'compare_all_extracted_cell_records', 'changes': changes,
            'scope_changed': scope(old_extract) != scope(new_extract),
            'unchanged_cells': sorted(loc for loc in a.keys() & b.keys() if a[loc] == b[loc]),
            'limit': 'Только зарегистрированные selections; остальные области не проверены'}


def locator_overlap(a, b):
    """True/False для известных координат, None при недостаточной точности."""
    if a == '*' or b == '*':
        return True
    if a == b:
        return True
    pattern = r"'((?:[^']|'')+)'!([A-Z]+)(\d+)(?::([A-Z]+)(\d+))?"
    aa, bb = list(re.finditer(pattern, a)), list(re.finditer(pattern, b))
    def column(s):
        value = 0
        for letter in s:
            value = value * 26 + ord(letter) - 64
        return value
    if aa and bb:
        # Частично распознанный locator не доказывает отсутствие пересечения.
        if re.sub(pattern, '', a).strip(' ;') or re.sub(pattern, '', b).strip(' ;'):
            return None
        for x in aa:
            for y in bb:
                if x[1] == y[1]:
                    if (max(column(x[2]), column(y[2])) <= min(column(x[4] or x[2]), column(y[4] or y[2]))
                            and max(int(x[3]), int(y[3])) <= min(int(x[5] or x[3]), int(y[5] or y[3]))):
                        return True
        return False
    pattern = r'physical-page:(\d+)/block:(\d+)(?:-(\d+))?'
    x, y = re.fullmatch(pattern, a), re.fullmatch(pattern, b)
    if x and y:
        return x[1] == y[1] and max(int(x[2]), int(y[2])) <= min(int(x[3] or x[2]), int(y[3] or y[2]))
    return None


def impact(project, data, event):
    """Обход явных доказательных/review ссылок; context_from не распространяет impact."""
    validate_change(data, event['change'])
    require(event['project_id'] == data['project_id'], 'Чужой проект в событии')
    change = event['change']
    source = change['source']
    comparison = compare_selection(project, data, source, change['replacement']) if change.get('replacement') else None
    locators = change['locators']
    if comparison is not None and change['type'] in {'corrected_value', 'changed_assumption', 'superseding_version', 'nonmaterial'}:
        locators = ['*'] if comparison['scope_changed'] else [c['locator'] for c in comparison['changes']]
    require(change['type'] != 'nonmaterial' or comparison is None or (not comparison['changes'] and not comparison['scope_changed']),
            'Изменённые ячейки нельзя молча объявить nonmaterial; выполните review')
    roots, edges, reasons, precision, root_paths = set(), {}, {}, [], {}
    def edge(a, b, reason):
        edges.setdefault(a, set()).add(b)
        reasons[(a, b)] = reason
    def hit(locator):
        values = [locator_overlap(locator, x) for x in locators]
        if any(x is True for x in values):
            return True
        if any(x is None for x in values):
            precision.append(locator)
            return True  # неизвестная точность → консервативный review
        return False
    source_node = f"source:{source['id']}@{source['version']}"
    reusable = []
    source_artifacts = next(s['artifact_ids'] for s in data['sources']
                            if s['id'] == source['id'] and s['version'] == source['version'])
    for artifact in data['artifacts']:
        obj = artifact_json(project, data, artifact['id'])
        if not obj or obj.get('source') != source:
            continue
        rows = obj.get('normalization', {}).get('rows', [])
        cells = [cell['locator'] for row in rows for cell in row.get('cells', {}).values() if 'locator' in cell]
        affected = not cells or any(hit(c) for c in cells)
        node = 'artifact:' + artifact['id']
        if affected and locators:
            roots.add(node)
            edge(source_node, node, 'Расчёт использует изменённый selection' if cells else 'Нет точного selection: проверить расчёт')
        elif cells:
            reusable.append({'artifact_id': artifact['id'], 'reason': 'Все выбранные расчётом ячейки вне изменения', 'locators': cells})
    for claim in data['claims']:
        node = 'claim:' + claim['id']
        for parent in claim['derived_from']:
            edge('claim:' + parent, node, 'derived_from')
        for parent in claim.get('review_dependencies', []):
            edge('claim:' + parent, node, 'review_dependency, не доказательное выведение')
        for ref in claim['evidence']:
            edge('artifact:' + ref['artifact_id'], node, 'evidence')
            if ((ref.get('source_id'), ref.get('source_version')) == (source['id'], source['version'])
                    or ('source_id' not in ref and ref['artifact_id'] in source_artifacts)):
                # Calculation provenance обрабатывается по фактическим mapped cells, не output-locator.
                if ref['artifact_id'] in source_artifacts and hit(ref['locator']):
                    roots.add(node)
                    edge(source_node, node, 'evidence ' + ref['locator'])
    for dep in data.get('artifact_dependencies', []):
        a, b = 'artifact:' + dep['from'], 'artifact:' + dep['to']
        if dep['from'] in source_artifacts and dep['to'] in {r['artifact_id'] for r in reusable}:
            continue  # точный mapped selection доказан неизменным
        edge(a, b, dep['reason'])
        if dep['from'] in source_artifacts and locators:
            roots.add(b)
            root_paths[b] = [source_node, a, b]
            precision.append('artifact_dependency:' + dep['from'])
    decision = data['decision']
    for condition in decision.get('conditions', []):
        node = 'condition:' + condition['id']
        for cid in condition['claim_ids']:
            edge('claim:' + cid, node, 'Условие пересмотра решения')
        for aid in condition['output_ids']:
            edge(node, 'output:' + aid, 'Текст использует условие решения')
    for item in decision.get('commitments', []):
        for cid in item.get('condition_ids', []):
            edge('condition:' + cid, 'commitment:' + item['id'], 'Обязательство проверяет это условие')
    paths = {n: root_paths.get(n, [source_node, n]) for n in sorted(roots)}
    queue = list(sorted(roots))
    for node in queue:
        for child in sorted(edges.get(node, [])):
            if child not in paths:  # Review backlinks допустимы; не рекурсия выведения.
                paths[child] = paths[node] + [child]
                queue.append(child)
    return {'event_id': event['id'], 'change_type': change['type'], 'source': source,
            'locators': locators, 'old_ground': change['old_ground'], 'new_ground': change['new_ground'],
            'affected': [{'node': n, 'path': path, 'reason': reasons.get((path[-2], n), 'Прямое изменение'),
                          'recomputation': n.startswith('artifact:') and change['type'] in {'corrected_value', 'changed_assumption', 'superseding_version'}}
                         for n, path in sorted(paths.items())],
            'reusable': reusable, 'precision': 'conservative' if precision else 'declared_links',
            'uncertain_locators': sorted(set(precision)), 'comparison': comparison,
            'limitations': 'Покрыты объявленные связи; координатор проверяет применимость и полноту. Отзыв поддержки не доказывает обратное; свежесть не равна ложности.'}


def register_event(data, event):
    require(event['project_id'] == data['project_id'], 'Событие относится к другому проекту')
    value = copy.deepcopy(event)
    value['fingerprint'] = digest({k: v for k, v in value.items() if k != 'fingerprint'})
    for existing in data['decision']['events']:
        if existing['id'] == value['id']:
            require(existing == value, 'Повтор event_id с другим содержимым: требуется сверка')
            return False
    data['decision']['events'].append(value)
    return True


def apply_change(project, data, event):
    result = copy.deepcopy(data)
    if not register_event(result, event):
        return result, False
    report = impact(project, result, event)
    affected = bool(report['affected'])
    result['decision']['reviews'].append({
        'id': 'review-' + event['id'], 'event_id': event['id'], 'status': 'needs_review',
        'reason': event['change']['reason'], 'impact': report,
        'owner_review_required': affected,
        'next_action': 'Проверить затронутые основания и подготовить отдельное предложение владельцу' if affected else 'Подтвердить отсутствие существенного влияния',
        'resolution_evidence': [],
    })
    if event['change']['type'] != 'freshness_review':
        affected_claims = {x['node'][6:] for x in report['affected'] if x['node'].startswith('claim:')}
        for claim in result['claims']:
            if claim['id'] in affected_claims and claim.get('status') not in {'superseded', 'withdrawn'}:
                claim['status'] = 'needs_review'
                claim['support_reason'] = event['id'] + ': ' + event['change']['reason']
    return result, True


def apply_event(project, data, event):
    """Готовит кандидат; публикация только штатным save после проверки артефактов."""
    if event['kind'] == 'evidence_change':
        return apply_change(project, data, event)
    result = copy.deepcopy(data)
    d = result['decision']
    if not register_event(result, event):
        return result, False
    channel = event['provenance']['kind']
    if event['kind'] == 'choice':
        simulated = channel == 'synthetic_instruction'
        require((simulated and data.get('evaluation', {}).get('synthetic') is True)
                or (channel == 'user_instruction' and event.get('authorized') is True),
                'Выбор требует инструкции пользователя; документ/tool-response не даёт authority')
        choice = event['choice']
        require(not simulated or choice.get('status', 'accepted') == 'accepted', 'Симуляция принятия не может подменять отказ')
        require(isinstance(choice.get('ground_ids'), list) and all(cid in {c['id'] for c in data['claims']} for cid in choice['ground_ids']),
                'Неизвестное основание выбора')
        record = {k: copy.deepcopy(choice[k]) for k in ('question', 'option', 'reason', 'owner', 'rejected_alternatives')}
        record.update(id=event['id'] + '-decision', status='simulated_accepted' if simulated else choice.get('status', 'accepted'),
                      instruction_event=event['id'], basis={'revision': data['revision'], 'state_sha256': data['state_sha256']},
                      grounds=[{'claim_id': cid, 'snapshot': copy.deepcopy(next(c for c in data['claims'] if c['id'] == cid))}
                               for cid in choice['ground_ids']])
        d['history'].append(record)
        d['status'] = record['status']
        d['owner'] = record['owner']
        if not simulated:
            d['human_confirmation'] = {'actor': event['actor'], 'authorized': True, 'at': event['at'],
                                       'evidence_artifact_id': event['provenance']['artifact_id'], 'test_fixture': False}
        for item in event.get('commitments', []):
            d['commitments'].append({**copy.deepcopy(item), 'decision_id': record['id']})
        for rid in event.get('resolves_reviews', []):
            review = next((r for r in d['reviews'] if r['id'] == rid), None)
            require(review is not None, 'Инструкция ссылается на неизвестный пересмотр')
            review['owner_review_required'] = False
    elif event['kind'] == 'completion':
        require(channel in {'user_instruction', 'synthetic_instruction', 'agent_review'}, 'Самоутверждение источника не завершает работу')
        item = next((c for c in d['commitments'] if c['id'] == event['commitment_id']), None)
        require(item is not None and item['status'] != 'completed', 'Обязательство не найдено или уже завершено')
        item.update(status='completed', completion_event=event['id'], completion_evidence=event['completion_evidence'],
                    completion_check=event['completion_check'])
    elif event['kind'] == 'review':
        require(channel == 'agent_review', 'Результат аналитического review должен иметь явное происхождение')
        item = next((r for r in d['reviews'] if r['id'] == event['review_id']), None)
        require(item is not None, 'Пересмотр не найден')
        for field in ('status', 'reason', 'next_action', 'resolution_evidence', 'owner_review_required'):
            item[field] = copy.deepcopy(event['resolution'][field])
        item['resolution_event'] = event['id']
        if 'proposed_option' in event['resolution']:
            d['proposed_option'] = event['resolution']['proposed_option']
    else:
        raise FollowupError('Неизвестный kind события')
    return result, True


def followup_view(data, as_of, timezone, clock):
    now = moment(as_of)
    require(clock in {'actual', 'simulated'}, 'Нужно явно выбрать actual/simulated clock')
    require(isinstance(timezone, str) and re.fullmatch(r'[+-]\d{2}:\d{2}', timezone), 'timezone — явное смещение ±HH:MM')
    sign = 1 if timezone[0] == '+' else -1
    require(now.utcoffset() == sign * timedelta(hours=int(timezone[1:3]), minutes=int(timezone[4:6])),
            'as-of и timezone должны совпадать')
    d = data['decision']
    commitments = {c['id']: c for c in d.get('commitments', [])}
    attention = []
    for item in commitments.values():
        reasons = []
        if item['status'] not in {'completed', 'cancelled'}:
            if item['due_at'] and now > moment(item['due_at']):
                reasons.append('overdue')
            elif item['due_at'] and now == moment(item['due_at']):
                reasons.append('due')
            if item['owner'] == 'unassigned':
                reasons.append('unassigned')
            if item['status'] == 'blocked' or any(commitments[x]['status'] != 'completed' for x in item['blocked_by']):
                reasons.append('blocked')
        attention.append({**item, 'attention': reasons})
    active_reviews = [r for r in d.get('reviews', []) if r['status'] == 'needs_review' or r['owner_review_required']]
    conditions = []
    for condition in d.get('conditions', []):
        reasons = []
        if condition.get('unresolved_reason'):
            reasons.append(condition['unresolved_reason'])
        if condition.get('review_after') and now >= moment(condition['review_after']):
            reasons.append('Наступило время проверки свежести; это не опровержение')
        related = [r['id'] for r in active_reviews if any(a['node'] == 'condition:' + condition['id'] for a in r['impact']['affected'])]
        if related:
            reasons.append('Изменились основания: ' + ', '.join(related))
        conditions.append({**condition, 'review_reasons': reasons})
    windows = []
    for metric in d.get('metrics', []):
        item = copy.deepcopy(metric)
        w = metric.get('window')
        item['window_state'] = 'not_started_or_unknown'
        if w:
            require(w['clock'] == clock, 'Нельзя оценивать симулированное окно фактическими часами или наоборот')
            item['window_state'] = 'ended_evidence_required' if now >= moment(w['end']) else ('open' if now >= moment(w['start']) else 'not_started')
        windows.append(item)
    ground_warnings = [{'claim_id': c['id'], 'status': c['status'], 'reason': c.get('support_reason', c.get('superseded_reason', 'Проверить основание'))}
                       for c in data['claims'] if c.get('status') in {'withdrawn', 'superseded', 'needs_review', 'contradicted'}]
    due_conditions = [c for c in conditions if c['review_reasons']]
    urgent = [c for c in attention if c['attention']]
    next_action = data['next_action']
    priority = 'Новых требований пересмотра и обязательств с сигналом внимания не найдено.'
    if active_reviews:
        next_action = active_reviews[0]['next_action']
        priority = 'Сначала пересмотр, поскольку он затрагивает основания решения: ' + active_reviews[0]['reason']
    elif due_conditions:
        next_action = due_conditions[0]['next_action']
        priority = 'Сначала условие решения: ' + '; '.join(due_conditions[0]['review_reasons'])
    elif urgent:
        next_action = 'Разобрать обязательство ' + urgent[0]['id'] + ': ' + urgent[0]['description']
        priority = 'Внимание требуется по явному сроку, владельцу или зависимости: ' + ', '.join(urgent[0]['attention'])
    return {'project_id': data['project_id'], 'revision': data.get('revision'),
            'synthetic_evaluation': data.get('evaluation', {}).get('synthetic', False),
            'as_of': as_of, 'timezone': timezone, 'clock': clock,
            'monitoring': 'Проверка только при вызове; фонового мониторинга и отправленных напоминаний нет',
            'decision_status': d['status'], 'proposed_option': d.get('proposed_option'),
            'history': d.get('history', []), 'commitments': attention, 'metrics': windows,
            'conditions': conditions, 'reviews': d.get('reviews', []), 'grounds_needing_attention': ground_warnings,
            'priority_reason': priority,
            'next_action': next_action}


def render_view(view):
    lines = [f"# Сопровождение — {view['project_id']}, revision {view['revision']}", '',
             f"Статус: **{view['decision_status']}**. Синтетическая оценка: {view['synthetic_evaluation']}.",
             f"На {view['as_of']}, timezone {view['timezone']}, clock={view['clock']}.",
             view['monitoring'], '', 'Предложение: ' + str(view['proposed_option']), '', '## История выбора', '']
    for h in view['history']:
        lines += [f"- {h['id']} ({h['status']}): {h['option']}. Ответственный: {h['owner']}. {h['reason']}",
                  f"  Инструкция {h['instruction_event']}; исходная revision {h['basis']['revision']} / {h['basis']['state_sha256']}."]
        for a in h['rejected_alternatives']:
            lines.append(f"  Альтернатива «{a['option']}»: {a['reason']}")
    lines += ['', '## Обязательства', '', '| ID / действие | Владелец | Срок / условие | Статус и внимание | Доказательство завершения |', '|---|---|---|---|---|']
    for c in view['commitments']:
        evidence = '; '.join(x['artifact_id'] + ': ' + x['locator'] for x in c.get('completion_evidence', [])) or 'не получено'
        lines.append(f"| {c['id']}: {c['description']} | {c['owner']} | {c['due_at'] or 'дата неизвестна'}; {c['due_condition']} | {c['status']}; {', '.join(c['attention']) or 'нет'}; зависимости {', '.join(c['blocked_by']) or 'нет'} | Нужно: {c['required_evidence']}. Получено: {evidence} |")
    lines += ['', '## Метрики и окна', '']
    for m in view['metrics']:
        lines.append(f"- {m['id']} [{m['gate']}]: {m['definition']}. Единица {m['unit']}; знаменатель {m['denominator']}; период {m['observation_period']}; сравнение {m['comparator']}; порог {m['threshold']}. Нужно: {m['needed_evidence']}. Окно: {m['window_state']}.")
    lines += ['', '## Условия пересмотра', '']
    for c in view['conditions']:
        lines.append(f"- {c['id']}: {c['description']}. Основания {', '.join(c['claim_ids'])}; метрики {', '.join(c['metric_ids'])}. Внимание: {'; '.join(c['review_reasons']) or 'новых причин нет'}. Действие: {c['next_action']}")
    lines += ['', '## Изменения оснований', '']
    for r in view['reviews']:
        lines.append(f"- {r['id']}: **{r['status']}**, требуется решение владельца: {r['owner_review_required']}. {r['reason']} Следующий шаг: {r['next_action']}")
    for g in view['grounds_needing_attention']:
        lines.append(f"- {g['claim_id']}: {g['status']}. {g['reason']}")
    lines += ['', view['priority_reason'], '', '**Следующее действие:** ' + view['next_action'], '']
    return '\n'.join(lines)


def reconcile(project, event_id):
    import project_state as ps
    result = ps.inspect_state(project)
    data = result['state']
    events = data['decision'].get('events', [])
    if any(e['id'] == event_id for e in events):
        return {'outcome': 'published', 'revision': data['revision'], 'event_id': event_id, 'warnings': result['warnings']}
    candidates = []
    for path in sorted((Path(project) / 'state/history').glob('r*.json')):
        if not re.fullmatch(r'r\d+\.json', path.name) or int(path.stem[1:]) <= data['revision']:
            continue
        try:
            candidate = ps._read_json(path, ps.DEFAULT_MAX_BYTES)
            ps.validate_state(project, candidate, require_saved=True)
            if any(e['id'] == event_id for e in candidate['decision'].get('events', [])):
                candidates.append({'revision': candidate['revision'], 'status': 'validated_publication_unknown'})
        except (ps.StateError, OSError):
            candidates.append({'file': path.name, 'status': 'invalid_candidate_no_raw_data'})
    return {'outcome': 'absent_from_current', 'revision': data['revision'], 'event_id': event_id,
            'candidates': candidates, 'warnings': result['warnings'],
            'next_action': 'Осмотреть вход, оставшиеся артефакты и наблюдения публикации/восстановления. History могла быть кандидатом или прежней публикацией до recovery; её статус неизвестен. Повтор только после сверки.'}


def main(argv=None):
    import project_state as ps
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['view', 'impact', 'reconcile', 'apply'])
    parser.add_argument('--project', required=True)
    parser.add_argument('--as-of')
    parser.add_argument('--timezone')
    parser.add_argument('--clock', choices=['actual', 'simulated'])
    parser.add_argument('--event', help='Событие JSON внутри проекта')
    parser.add_argument('--event-id')
    parser.add_argument('--draft', help='Новый путь кандидата внутри проекта, без перезаписи')
    parser.add_argument('--markdown', action='store_true')
    args = parser.parse_args(argv)
    try:
        data = ps.load_state(args.project)
        if args.command == 'reconcile':
            text_value(args.event_id, 'event-id')
            result = reconcile(args.project, args.event_id)
        elif args.command in {'impact', 'apply'}:
            event = ps._read_json(ps.scoped_path(args.project, args.event), ps.DEFAULT_MAX_BYTES)
            if args.command == 'impact':
                result = impact(args.project, data, event)
            else:
                candidate, changed = apply_event(args.project, data, event)
                if changed:
                    text_value(args.draft, 'draft')
                    ps.validate_state(args.project, candidate)
                    ps._write_new(ps.scoped_path(args.project, args.draft), ps._json_bytes(candidate, pretty=True))
                result = {'changed': changed, 'published': False, 'draft': args.draft if changed else None,
                          'next_action': 'Проверить кандидат и выполнить project_state save' if changed else 'Событие уже в опубликованном состоянии; повтор не нужен'}
        else:
            result = followup_view(data, args.as_of, args.timezone, args.clock)
        print(render_view(result) if args.markdown and args.command == 'view' else json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ps.StateError, FollowupError, OSError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())
