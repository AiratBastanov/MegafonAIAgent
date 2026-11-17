"""Границы decision/impact; не доказательство универсальной защиты LLM."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import project_state as ps
import decision_followup as df


class FollowupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / 'sample'
        self.project.mkdir()
        self.data = {'schema_version': 1, 'project_id': 'sample', 'objective': 'Выбрать действие',
                     'decision_question': 'Продолжать?', 'stage': 'awaiting_decision', 'next_action': 'Решение владельца',
                     'completed': [], 'unresolved_questions': [], 'pending_actions': [], 'artifacts': [], 'sources': [],
                     'claims': [], 'evaluation': {'synthetic': True}, 'artifact_dependencies': [],
                     'decision': {'format_version': 2, 'status': 'awaiting_decision', 'question': 'Продолжать?',
                                  'proposed_option': 'Проверить', 'owner': 'unassigned', 'history': [], 'events': [],
                                  'commitments': [], 'metrics': [], 'conditions': [], 'reviews': []}}
        self.add('A', 'source.txt', 'Описание возможностей. Учебное.')
        self.add('I', 'instruction.txt', 'Учебная инструкция владельца только для симуляции')
        self.add('O', 'output.md', 'Предложение')
        self.data['sources'] = [{'id': 'S', 'version': 1, 'artifact_ids': ['A'], 'synthetic': True}]
        self.data['claims'] = [dict(id='C', kind='source_fact', text='Возможность по описанию', synthetic=True,
                                    evidence=[{'artifact_id': 'A', 'locator': 'line:1'}], derived_from=[]),
                               dict(id='R', kind='recommendation', text='Условная рекомендация', synthetic=True,
                                    evidence=[], derived_from=['C'])]
        self.data['decision']['conditions'] = [dict(id='G', description='Приёмка возможности', claim_ids=['R'],
                                                    metric_ids=[], output_ids=['O'], next_action='Проверить')]
        self.initial = ps.save_state(self.project, self.data)

    def add(self, aid, path, content):
        p = self.project / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(content, ensure_ascii=False) if isinstance(content, dict) else content, encoding='utf-8')
        self.data['artifacts'].append(ps.reference(self.project, path, aid))

    def event(self, kind='choice', eid='E'):
        base = dict(id=eid, project_id='sample', at='2026-11-16T15:00:00+03:00', kind=kind,
                    provenance={'kind': 'synthetic_instruction' if kind == 'choice' else 'source_material',
                                'artifact_id': 'I', 'locator': 'line:1'})
        if kind == 'choice':
            base['choice'] = dict(question='Продолжать?', option='Проверить', reason='Ограничить неизвестность', owner='учебная роль',
                                  rejected_alternatives=[{'option': 'Масштабировать', 'reason': 'Нет данных'}], ground_ids=['C', 'R'])
            base['commitments'] = [dict(id='K', description='Проверить описание', owner='unassigned', due_at=None,
                                        due_condition='До приглашения', status='pending', required_evidence='Протокол приёмки',
                                        completion_evidence=[], blocked_by=[], condition_ids=['G'])]
        if kind == 'evidence_change':
            base['change'] = dict(type='withdrawn_support', source={'id': 'S', 'version': 1}, locators=['line:1'],
                                  reason='Отозвана поддержка', old_ground='Описание', new_ground='Поддержка отозвана',
                                  applicability='Тот же прототип, не другая компания')
        return base

    def accepted(self):
        data, _ = df.apply_event(self.project, self.initial, self.event())
        return ps.save_state(self.project, data)

    def xlsx_pair(self, unit_changed=False, value_changed=True):
        for v in (1, 2):
            extracted = {'format': 'xlsx', 'selection': {'unit': 'RUB' if v == 1 or not unit_changed else 'USD'},
                         'sheets': [{'name': 'E', 'state': 'visible', 'cells': [
                             {'locator': "'E'!A1", 'value': 30 if v == 1 or not value_changed else 90},
                             {'locator': "'F'!A1", 'value': 8}]}]}
            self.add('X' + str(v), f'x{v}.json', extracted)
            self.data['sources'].append({'id': 'X', 'version': v, 'artifact_ids': ['X' + str(v)], 'synthetic': True})
        self.add('CALC', 'calc.json', {'source': {'id': 'X', 'version': 1}, 'normalization': {
            'rows': [{'cells': {'funnel': {'locator': "'F'!A1"}}}]}})
        self.data['claims'][0]['evidence'] = [{'artifact_id': 'X1', 'locator': "'E'!A1", 'source_id': 'X', 'source_version': 1}]
        self.data['claims'].append(dict(id='F', kind='computed', text='Воронка', evidence=[{'artifact_id': 'CALC', 'locator': 'result'}],
                                       derived_from=[], context_from=['C'], synthetic=True))
        event = self.event('evidence_change')
        event['change'].update(type='corrected_value', source={'id': 'X', 'version': 1},
                               replacement={'id': 'X', 'version': 2}, locators=["'E'!A1"])
        return event

    def test_artifact_only_withdrawal_reaches_claim_condition_output(self):
        report = df.impact(self.project, self.data, self.event('evidence_change'))
        self.assertEqual({a['node'] for a in report['affected']}, {'claim:C', 'claim:R', 'condition:G', 'output:O'})
        self.assertTrue(all(not x['recomputation'] for x in report['affected']))

    def test_selection_reuses_funnel_but_reaches_economic_review_link(self):
        event = self.xlsx_pair()
        self.data['claims'][1]['derived_from'] = []
        self.data['claims'][1]['review_dependencies'] = ['C']
        self.data['claims'][0]['review_dependencies'] = ['R']  # допустимый review backlink
        ps.validate_state(self.project, self.data)
        report = df.impact(self.project, self.data, event)
        affected = {x['node'] for x in report['affected']}
        self.assertIn('condition:G', affected)
        self.assertNotIn('claim:F', affected)
        self.assertEqual(report['reusable'][0]['artifact_id'], 'CALC')
        self.assertEqual(report['comparison']['changes'][0]['old']['value'], 30)

    def test_registering_impact_report_does_not_turn_it_into_calculation(self):
        event = self.xlsx_pair()
        before = df.impact(self.project, self.data, event)
        self.assertEqual(before['record_type'], 'decision_impact')
        self.add('IMPACT', 'impact.json', before)
        after = df.impact(self.project, self.data, event)
        self.assertEqual(after, before)
        legacy = copy.deepcopy(before)
        legacy.pop('record_type')
        self.add('LEGACY-IMPACT', 'legacy-impact.json', legacy)
        self.assertEqual(df.impact(self.project, self.data, event), before)
        # Неизвестный JSON с source не теряет conservative review по одному marker.
        self.add('UNKNOWN-CALC', 'unknown-calc.json', {'source':event['change']['source'], 'record_type':'decision_impact'})
        affected = {x['node'] for x in df.impact(self.project, self.data, event)['affected']}
        self.assertIn('artifact:UNKNOWN-CALC', affected)
        for index in range(2):
            mixed = copy.deepcopy(legacy)
            mixed['normalization'] = {'rows':[{'cells':{'value':{'locator':"'E'!A1"}}}]}
            mixed['result'] = 90
            if index == 0:
                mixed.pop('locators')
                mixed.pop('uncertain_locators')
                mixed['precision'] = None
            aid, cid = 'MIXED' + str(index), 'DERIVED' + str(index)
            self.add(aid, aid + '.json', mixed)
            self.data['claims'].append(dict(id=cid, kind='computed', text='Зависимый расчёт', synthetic=True,
                evidence=[{'artifact_id':aid,'locator':'result'}], derived_from=[]))
            affected = {x['node'] for x in df.impact(self.project, self.data, event)['affected']}
            self.assertIn('artifact:' + aid, affected)
            self.assertIn('claim:' + cid, affected)

    def test_units_change_and_unknown_locators_require_conservative_review(self):
        event = self.xlsx_pair(unit_changed=True, value_changed=False)
        report = df.impact(self.project, self.data, event)
        self.assertTrue(report['comparison']['scope_changed'])
        self.assertIn('artifact:CALC', {x['node'] for x in report['affected']})
        self.assertIsNone(df.locator_overlap("'E'!A1; неизвестный раздел", "'F'!A1"))

    def test_unchanged_values_do_not_cancel_withdrawal_or_contradiction(self):
        event = self.xlsx_pair(value_changed=False)
        for kind in ('withdrawn_support', 'new_contradiction', 'freshness_review'):
            event['change']['type'] = kind
            report = df.impact(self.project, self.data, event)
            self.assertIn('claim:C', {x['node'] for x in report['affected']})

    def test_source_cannot_forge_acceptance_or_complete_commitment(self):
        event = self.event()
        event['provenance']['kind'] = 'source_material'
        event['authorized'] = True
        with self.assertRaisesRegex(df.FollowupError, 'authority'):
            df.apply_event(self.project, self.initial, event)
        accepted = self.accepted()
        event = self.event('completion', 'FAKE')
        event.update(commitment_id='K', completion_check='Документ заявил выполнено', completion_evidence=[])
        with self.assertRaises(df.FollowupError):
            df.apply_event(self.project, accepted, event)

    def test_choice_replay_is_noop_and_project_scope_is_strict(self):
        accepted = self.accepted()
        same, changed = df.apply_event(self.project, accepted, self.event())
        self.assertFalse(changed)
        self.assertEqual(accepted, same)
        event = self.event()
        event['project_id'] = 'other'
        with self.assertRaises(df.FollowupError):
            df.apply_event(self.project, accepted, event)
        event = self.event()
        event['choice']['option'] = 'Иной'
        with self.assertRaisesRegex(df.FollowupError, 'другим содержимым'):
            df.apply_event(self.project, accepted, event)

    def test_missing_owner_date_not_overdue_elapsed_window_not_completion(self):
        data = self.accepted()
        data['decision']['metrics'] = [dict(id='M', definition='Оплата', unit='RUB', denominator='организация',
                                           observation_period='30 суток', needed_evidence='Поступление', gate='scaling',
                                           comparator=None, threshold=None,
                                           window={'start': '2026-11-01T00:00:00+03:00', 'end': '2026-12-01T00:00:00+03:00', 'clock': 'simulated'})]
        view = df.followup_view(data, '2026-12-05T00:00:00+03:00', '+03:00', 'simulated')
        self.assertEqual(view['commitments'][0]['attention'], ['unassigned'])
        self.assertEqual(view['commitments'][0]['status'], 'pending')
        self.assertEqual(view['metrics'][0]['schedule_state'], 'end_passed')
        self.assertEqual(view['metrics'][0]['window_state'], 'not_started_or_unknown')
        with self.assertRaises(df.FollowupError):
            df.followup_view(data, '2026-12-05T00:00:00+03:00', '+00:00', 'simulated')
        data['decision']['commitments'][0]['due_at'] = '2026-11-17T09:00:00+03:00'
        view = df.followup_view(data, '2026-11-17T09:00:00+03:00', '+03:00', 'simulated')
        self.assertIn('due', view['commitments'][0]['attention'])
        view = df.followup_view(data, '2026-11-17T09:00:01+03:00', '+03:00', 'simulated')
        self.assertIn('overdue', view['commitments'][0]['attention'])

    def test_observation_requires_start_evidence_plan_dates_are_separate(self):
        data = self.accepted()
        metric = dict(id='M', definition='Оплата', unit='RUB', denominator='организация',
                      observation_period='30 суток', needed_evidence='Поступление', gate='scaling',
                      comparator=None, threshold=None,
                      window={'start': '2026-11-01T00:00:00+03:00', 'end': '2026-12-01T00:00:00+03:00', 'clock': 'simulated'})
        data['decision']['metrics'] = [metric]
        for when, schedule in [('2026-10-31', 'before_start'), ('2026-11-01', 'within_dates'), ('2026-12-01', 'end_passed')]:
            view = df.followup_view(data, when+'T00:00:00+03:00', '+03:00', 'simulated')
            self.assertEqual(view['metrics'][0]['schedule_state'], schedule)
            self.assertEqual(view['metrics'][0]['window_state'], 'not_started_or_unknown')
            self.assertEqual(view['commitments'][0]['status'], 'pending')
        metric['window']['kind'] = 'observation'
        with self.assertRaisesRegex(ps.StateError, 'evidence начала'):
            ps.validate_state(self.project, data)
        metric['window']['start_evidence'] = [{'artifact_id': 'MISSING', 'locator': 'line:1'}]
        with self.assertRaises(ps.StateError):
            ps.validate_state(self.project, data)
        # Компонентный fixture свидетельства; validator проверяет ссылку, не истинность текста.
        metric['window']['start_evidence'] = [{'artifact_id': 'A', 'locator': 'line:1'}]
        ps.validate_state(self.project, data)
        for when, state in [('2026-10-31', 'not_started'), ('2026-11-01', 'open'), ('2026-12-01', 'ended_evidence_required')]:
            view = df.followup_view(data, when+'T00:00:00+03:00', '+03:00', 'simulated')
            self.assertEqual(view['metrics'][0]['window_state'], state)
            self.assertEqual(view['commitments'][0]['status'], 'pending')
        with self.assertRaises(df.FollowupError):
            df.followup_view(data, '2026-12-01T00:00:00+03:00', '+03:00', 'actual')
        metric['window'] = None
        self.assertEqual(df.followup_view(data, '2026-12-01T00:00:00+03:00', '+03:00', 'simulated')['metrics'][0]['schedule_state'], 'not_scheduled')

    def test_numeric_materiality_review_and_existing_owner_requirement(self):
        correction = self.xlsx_pair()
        self.add('CHECK', 'checked.txt', 'Сверены текущие 90 и расчёт; повтор не меняет принятое основание')
        self.data['claims'].append(dict(id='CURRENT', kind='computed', text='Текущий расчёт на 90',
            evidence=[{'artifact_id':'X2', 'locator':"'E'!A1", 'source_id':'X', 'source_version':2}],
            derived_from=['C'], synthetic=True))
        self.data['claims'][1]['derived_from'] = ['CURRENT']
        base = ps.save_state(self.project, self.data)
        chosen, _ = df.apply_event(self.project, base, self.event())
        chosen = ps.save_state(self.project, chosen)
        correction['id'] = 'REPEAT'
        pending, _ = df.apply_event(self.project, chosen, correction)
        self.assertFalse(pending['decision']['reviews'][-1]['owner_review_required'])
        view = df.followup_view(pending, '2026-12-05T00:00:00+03:00', '+03:00', 'simulated')
        self.assertIn('аналитическая проверка', view['priority_reason'])
        pending = ps.save_state(self.project, pending)
        self.assertEqual(pending['claims'][-1]['status'], 'needs_review')
        close = dict(id='CHECK-REPEAT', project_id='sample', kind='review', at='2026-12-05T00:00:00+03:00',
            provenance={'kind':'agent_review','artifact_id':'CHECK','locator':'line:1'}, review_id='review-REPEAT',
            resolution={'status':'reviewed_unchanged','reason':'Сверены текущие 90 и действующий расчёт',
                        'next_action':'Продолжить прежние обязательства','owner_review_required':False,
                        'resolution_evidence':[{'artifact_id':'CHECK','locator':'line:1'}, {'artifact_id':'X2','locator':"'E'!A1"}]})
        closed, _ = df.apply_event(self.project, pending, close)
        closed = ps.save_state(self.project, closed)
        self.assertEqual(closed['claims'], chosen['claims'])
        self.assertEqual(closed['decision']['history'], chosen['decision']['history'])
        self.assertEqual(closed['decision']['commitments'], chosen['decision']['commitments'])
        self.assertFalse(df.apply_event(self.project, closed, correction)[1])
        # Независимый материальный отзыв остаётся true при повторе и его закрытии.
        withdrawal = copy.deepcopy(correction)
        withdrawal['id'] = 'WITHDRAW'
        withdrawal['change']['type'] = 'withdrawn_support'
        active, _ = df.apply_event(self.project, closed, withdrawal)
        active = ps.save_state(self.project, active)
        true_review = copy.deepcopy(active['decision']['reviews'][-1])
        again = copy.deepcopy(correction)
        again['id'] = 'REPEAT2'
        active, _ = df.apply_event(self.project, active, again)
        active = ps.save_state(self.project, active)
        close2 = copy.deepcopy(close)
        close2.update(id='CHECK-REPEAT2', review_id='review-REPEAT2')
        active, _ = df.apply_event(self.project, active, close2)
        active = ps.save_state(self.project, active)
        self.assertEqual(active['decision']['reviews'][1], true_review)
        self.assertEqual(active['claims'][-1]['status'], 'needs_review')
        bad = copy.deepcopy(active)
        bad['decision']['reviews'][1]['owner_review_required'] = False
        with self.assertRaisesRegex(ps.StateError, 'владельца'):
            ps.save_state(self.project, bad)
        # Действительно новая величина 120 вместо 90 требует отдельного анализа.
        extract = json.loads((self.project/'x2.json').read_text(encoding='utf-8'))
        extract['sheets'][0]['cells'][0]['value'] = 120
        (self.project/'x3.json').write_text(json.dumps(extract), encoding='utf-8')
        active['artifacts'].append(ps.reference(self.project, 'x3.json', 'X3'))
        active['sources'].append({'id':'X','version':3,'artifact_ids':['X3'],'synthetic':True})
        active = ps.save_state(self.project, active)
        new_value = copy.deepcopy(correction)
        new_value['id'] = 'NEXT-VERSION'
        new_value['change'].update(type='superseding_version', source={'id':'X','version':2}, replacement={'id':'X','version':3})
        next_pending, _ = df.apply_event(self.project, active, new_value)
        self.assertFalse(next_pending['decision']['reviews'][-1]['owner_review_required'])
        new_review = copy.deepcopy(close)
        new_review.update(id='REVIEW-NEXT', review_id='review-NEXT-VERSION')
        new_review['resolution'].update(status='revised', owner_review_required=True,
            reason='120 вместо 90 меняет основание; компонентный контроль явной эскалации')
        revised, _ = df.apply_event(self.project, next_pending, new_review)
        revised = ps.save_state(self.project, revised)
        self.assertTrue(revised['decision']['reviews'][-1]['owner_review_required'])

    def test_overlapping_numeric_reviews_restore_flags_in_both_orders(self):
        correction = self.xlsx_pair()
        self.add('CHECK', 'checked.txt', 'Компонентный fixture аналитической сверки')
        base = ps.save_state(self.project, self.data)
        for order in [('ONE', 'TWO'), ('TWO', 'ONE')]:
            with self.subTest(order=order):
                current = copy.deepcopy(base)
                for eid in ('ONE', 'TWO'):
                    event = copy.deepcopy(correction)
                    event['id'] = eid
                    current, _ = df.apply_event(self.project, current, event)
                for index, eid in enumerate(order):
                    close = dict(id='CLOSE-'+eid, project_id='sample', kind='review', at='2026-12-05T00:00:00+03:00',
                        provenance={'kind':'agent_review','artifact_id':'CHECK','locator':'line:1'}, review_id='review-'+eid,
                        resolution={'status':'reviewed_unchanged','reason':'Текущий расчёт и выводы сверены',
                                    'next_action':'Продолжить прежние обязательства','owner_review_required':False,
                                    'resolution_evidence':[{'artifact_id':'CHECK','locator':'line:1'}]})
                    current, _ = df.apply_event(self.project, current, close)
                    ps.validate_state(self.project, current)
                    df.validate_transition(base, current)
                    if index == 0:
                        self.assertEqual(current['claims'][0]['status'], 'needs_review')
                    else:
                        self.assertEqual(current['claims'], base['claims'])

    def test_history_and_pinned_artifacts_cannot_be_rewritten(self):
        data = self.accepted()
        data['decision']['history'][0]['option'] = 'Самостоятельно изменить выбор'
        with self.assertRaises(ps.StateError):
            ps.save_state(self.project, data)
        data = ps.load_state(self.project)
        (self.project / 'replacement.txt').write_text('Другие данные', encoding='utf-8')
        data['artifacts'][0] = ps.reference(self.project, 'replacement.txt', 'A')
        with self.assertRaisesRegex(ps.StateError, 'переназначить'):
            ps.validate_state(self.project, data)

    def test_missing_refs_cycles_and_duplicate_decision_rejected(self):
        data = self.accepted()
        duplicate = copy.deepcopy(data['decision']['history'][0])
        duplicate['id'] = 'OTHER'
        data['decision']['history'].append(duplicate)
        with self.assertRaisesRegex(ps.StateError, 'два решения'):
            ps.validate_state(self.project, data)
        data = ps.load_state(self.project)
        data['decision']['commitments'][0]['blocked_by'] = ['K']
        with self.assertRaisesRegex(ps.StateError, 'Цикл'):
            ps.validate_state(self.project, data)
        data['decision']['commitments'][0]['blocked_by'] = []
        data['decision']['conditions'][0]['claim_ids'] = ['MISSING']
        with self.assertRaises(ps.StateError):
            ps.validate_state(self.project, data)
        data = ps.load_state(self.project)
        data['artifact_dependencies'] = [{'from': 'A', 'to': 'O', 'reason': 'calc'}, {'from': 'O', 'to': 'A', 'reason': 'cycle'}]
        with self.assertRaisesRegex(ps.StateError, 'Цикл'):
            ps.validate_state(self.project, data)

    def test_review_cannot_erase_human_requirement(self):
        data, _ = df.apply_change(self.project, self.accepted(), self.event('evidence_change', 'W'))
        published = ps.save_state(self.project, data)
        data['decision']['reviews'] = []
        with self.assertRaises(ps.StateError):
            ps.save_state(self.project, data)
        data = copy.deepcopy(published)
        data['decision']['reviews'][0]['owner_review_required'] = False
        with self.assertRaisesRegex(ps.StateError, 'владельца'):
            ps.save_state(self.project, data)

    def test_completion_requires_evidence_and_check_event(self):
        data = self.accepted()
        event = self.event('completion', 'DONE')
        event['provenance']['kind'] = 'agent_review'
        event.update(commitment_id='K', completion_check='Проверен протокол', completion_evidence=[])
        bad, _ = df.apply_event(self.project, data, event)
        with self.assertRaisesRegex(ps.StateError, 'доказательство'):
            ps.save_state(self.project, bad)
        event['completion_evidence'] = [{'artifact_id': 'A', 'locator': 'line:1'}]
        valid, _ = df.apply_event(self.project, data, event)
        ps.save_state(self.project, valid)
        self.assertEqual(df.reconcile(self.project, 'DONE')['outcome'], 'published')

    def test_invalid_source_version_not_silently_applied(self):
        event = self.event('evidence_change')
        event['change']['source']['version'] = 77
        with self.assertRaises(df.FollowupError):
            df.impact(self.project, self.data, event)

    def test_explicit_source_artifact_dependency_reaches_calculation(self):
        self.add('CALC', 'dependent.json', {'result': 'неполная нормализация'})
        self.data['artifact_dependencies'] = [{'from': 'A', 'to': 'CALC', 'reason': 'Расчёт использует источник'}]
        self.data['claims'][0]['evidence'] = [{'artifact_id': 'CALC', 'locator': 'result'}]
        report = df.impact(self.project, self.data, self.event('evidence_change'))
        self.assertIn('claim:C', {x['node'] for x in report['affected']})
        self.assertEqual(report['precision'], 'conservative')

    def test_incomplete_review_or_choice_cannot_be_published(self):
        data = self.accepted()
        orphan = self.event('choice', 'ORPHAN')
        df.register_event(data, orphan)
        with self.assertRaisesRegex(ps.StateError, 'Неполное событие choice'):
            ps.save_state(self.project, data)
        data, _ = df.apply_change(self.project, self.accepted_base(), self.event('evidence_change', 'W'))
        orphan = dict(id='BAD-REVIEW', project_id='sample', kind='review', at='2026-11-16T15:00:00+03:00',
                      provenance={'kind': 'agent_review', 'artifact_id': 'I', 'locator': 'line:1'}, review_id='review-W')
        df.register_event(data, orphan)
        with self.assertRaisesRegex(ps.StateError, 'Неполное событие review'):
            ps.validate_state(self.project, data)

    def accepted_base(self):
        return ps.load_state(self.project)

    def test_real_rejection_cannot_be_upgraded_to_acceptance(self):
        event = self.event()
        event['provenance']['kind'] = 'user_instruction'
        event.update(authorized=True, actor='учебный актор component test')
        event['choice']['status'] = 'rejected'
        data, _ = df.apply_event(self.project, self.initial, event)
        data['decision']['status'] = data['decision']['history'][0]['status'] = 'accepted'
        with self.assertRaisesRegex(ps.StateError, 'Статус истории'):
            ps.validate_state(self.project, data)

    def test_new_owner_choice_resolves_only_named_review(self):
        accepted = self.accepted()
        data, _ = df.apply_change(self.project, accepted, self.event('evidence_change', 'W1'))
        data, _ = df.apply_change(self.project, data, self.event('evidence_change', 'W2'))
        previous = ps.save_state(self.project, data)
        event = self.event(eid='OWNER-2')
        event['commitments'] = []
        event['resolves_reviews'] = ['review-W1']
        updated, _ = df.apply_event(self.project, previous, event)
        saved = ps.save_state(self.project, updated)
        self.assertEqual(saved['decision']['history'][0], accepted['decision']['history'][0])
        self.assertEqual(len(saved['decision']['history']), 2)
        self.assertFalse(saved['decision']['reviews'][0]['owner_review_required'])
        self.assertTrue(saved['decision']['reviews'][1]['owner_review_required'])

    def test_draft_cannot_forge_review_provenance_or_completion_binding(self):
        data, _ = df.apply_change(self.project, self.accepted(), self.event('evidence_change', 'W'))
        review = dict(id='REVIEW', kind='review', project_id='sample', at='2026-11-16T15:00:00+03:00',
                      provenance={'kind': 'agent_review', 'artifact_id': 'I', 'locator': 'line:1'}, review_id='review-W',
                      resolution={'status': 'reviewed_unchanged', 'reason': 'Проверено', 'next_action': 'Решение владельца',
                                  'owner_review_required': True, 'resolution_evidence': [{'artifact_id': 'A', 'locator': 'line:1'}]})
        valid, _ = df.apply_event(self.project, data, review)
        ps.validate_state(self.project, valid)
        valid['decision']['events'][-1]['provenance']['kind'] = 'source_material'
        item = valid['decision']['events'][-1]
        item['fingerprint'] = df.digest({k: v for k, v in item.items() if k != 'fingerprint'})
        with self.assertRaisesRegex(ps.StateError, 'Документ'):
            ps.validate_state(self.project, valid)
        event = self.event('completion', 'DONE')
        event['provenance']['kind'] = 'agent_review'
        event.update(commitment_id='K', completion_check='Проверка протокола', completion_evidence=[{'artifact_id': 'A', 'locator': 'line:1'}])
        valid, _ = df.apply_event(self.project, self.accepted_base(), event)
        valid['decision']['commitments'][0]['completion_evidence'] = [{'artifact_id': 'I', 'locator': 'иной документ'}]
        with self.assertRaisesRegex(ps.StateError, 'не соответствует событию'):
            ps.validate_state(self.project, valid)


if __name__ == '__main__':
    unittest.main()
