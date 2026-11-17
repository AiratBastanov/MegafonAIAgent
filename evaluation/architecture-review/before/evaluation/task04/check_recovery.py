"""Локальные injected failures на Windows/Python, с отдельным CLI loader.

Не имитация power loss и не fresh Codex. Все файлы — собственные fixtures.
"""
from pathlib import Path
import copy
import json
import os
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import project_state as ps
import decision_followup as df


def cli(project, command, *extra):
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/project_state.py'), command,
                             '--project', str(project), *extra], capture_output=True, encoding='utf-8',
                            env={**os.environ, 'PYTHONIOENCODING': 'cp1251'}, timeout=30)
    payload = json.loads(result.stdout if result.returncode == 0 else result.stderr)
    return {'returncode': result.returncode, 'result': payload}


def setup(folder):
    folder.mkdir(parents=True, exist_ok=False)
    (folder / 'source.txt').write_text('Синтетическое описание возможности\n', encoding='utf-8')
    (folder / 'event.txt').write_text('Синтетический отзыв поддержки, не утверждение решения\n', encoding='utf-8')
    data = dict(schema_version=1, project_id=folder.name, objective='Проверка публикации', decision_question='Что проверить?',
                stage='awaiting_decision', next_action='Ждать фактическое решение', completed=[], pending_actions=[], unresolved_questions=[],
                artifacts=[ps.reference(folder, 'source.txt', 'A'), ps.reference(folder, 'event.txt', 'I')],
                sources=[dict(id='S', version=1, artifact_ids=['A'], synthetic=True)],
                claims=[dict(id='C', kind='source_fact', text='Описание', synthetic=True, derived_from=[],
                             evidence=[dict(artifact_id='A', locator='line:1', source_id='S', source_version=1)])],
                decision=dict(format_version=2, status='awaiting_decision', question='Что проверить?', proposed_option='Проверить',
                              owner='unassigned', history=[], events=[], commitments=[], metrics=[], conditions=[], reviews=[]))
    first = ps.save_state(folder, data)
    data['completed'].append('Исходный пакет проверен')
    second = ps.save_state(folder, data)
    event = dict(id='W', project_id=folder.name, kind='evidence_change', at='2026-11-16T15:00:00+03:00',
                 provenance=dict(kind='source_material', artifact_id='I', locator='line:1'),
                 change=dict(type='withdrawn_support', source=dict(id='S', version=1), locators=['line:1'],
                             reason='Отзыв поддержки', old_ground='Описание', new_ground='Не подтверждено', applicability='Учебный пакет'))
    return first, second, df.apply_change(folder, second, event)[0]


def run_scenarios(base):
    results = {}
    for name in ('artifact_before_save', 'partial_history', 'previous_replace', 'current_replace', 'missing_evidence', 'corrupt_current'):
        folder = base / name.replace('_', '-')
        first, second, candidate = setup(folder)
        details = {'injected': True, 'platform': sys.platform, 'interpreter': sys.executable, 'before_revision': second['revision']}
        if name == 'artifact_before_save':
            path = folder / 'unpublished.txt'
            path.write_text('Локальный результат до публикации', encoding='utf-8')
            candidate['artifacts'].append(ps.reference(folder, path.name, 'UNPUBLISHED'))
            details['boundary'] = 'Артефакт записан; save намеренно ещё не вызывался'
        elif name == 'partial_history':
            actual = ps._write_new
            def partial(path, content):
                if path.name == 'r000003.json':
                    path.write_bytes(b'{"partial":')
                    raise OSError('injected partial history write')
                return actual(path, content)
            with patch.object(ps, '_write_new', side_effect=partial):
                try:
                    ps.save_state(folder, candidate)
                    raise AssertionError('Failure was not injected')
                except OSError:
                    pass
            (folder / 'state/.leftover.tmp').write_text('{', encoding='utf-8')
        elif name in {'previous_replace', 'current_replace'}:
            actual = os.replace
            target = 'previous.json' if name == 'previous_replace' else 'current.json'
            def fail(source, destination):
                if Path(destination).name == target:
                    raise PermissionError('injected Windows replacement error')
                return actual(source, destination)
            with patch.object(ps.os, 'replace', side_effect=fail):
                try:
                    ps.save_state(folder, candidate)
                    raise AssertionError('Failure was not injected')
                except PermissionError:
                    pass
        elif name == 'missing_evidence':
            extra = folder / 'new-only.txt'
            extra.write_text('Новая закреплённая версия', encoding='utf-8')
            candidate['artifacts'].append(ps.reference(folder, extra.name, 'EXTRA'))
            ps.save_state(folder, candidate)
            # Fixture сохраняется под другим именем; пользовательские файлы не удаляются.
            extra.rename(folder / 'retained-missing-evidence.txt')
        else:
            ps.save_state(folder, candidate)
            marker = 'SYNTHETIC_' + 'SECRET_RECOVERY_TASK04'
            (folder / 'state/current.json').write_text('{"injected":"' + marker, encoding='utf-8')
        observed = cli(folder, 'load')
        details['load_after_failure'] = observed
        if name in {'missing_evidence', 'corrupt_current'}:
            assert observed['returncode'] == 2
            assert cli(folder, 'load', '--previous')['result']['state']['revision'] == 2
            recovery = cli(folder, 'recover', '--previous')
            assert recovery['returncode'] == 0 and recovery['result']['state']['revision'] == 2
            details['explicit_recovery'] = recovery
            assert cli(folder, 'load')['result']['state']['revision'] == 2
            details['reconcile_after_recovery'] = df.reconcile(folder, 'W')
            assert details['reconcile_after_recovery']['outcome'] == 'absent_from_current'
            # Валидная r3 до corrupt_current действительно публиковалась.
            # History сама не доказывает ни публикацию, ни её отсутствие.
            if name == 'corrupt_current':
                assert details['reconcile_after_recovery']['candidates'][0]['status'] == 'validated_publication_unknown'
            diagnostics = list((folder / 'state').glob('replaced-current-*.json'))
            assert diagnostics and all(json.loads(p.read_text(encoding='utf-8'))['raw_preserved'] is False for p in diagnostics)
            if name == 'corrupt_current':
                assert all(marker not in p.read_text(encoding='utf-8') for p in (folder / 'state').rglob('*.json'))
            details['safe_diagnostics'] = [p.name for p in diagnostics]
        else:
            assert observed['returncode'] == 0 and observed['result']['state']['revision'] == 2
            if name == 'previous_replace':
                assert cli(folder, 'load', '--previous')['result']['state']['revision'] == 1
            if name == 'current_replace':
                assert cli(folder, 'load', '--previous')['result']['state']['revision'] == 2
            details['reconcile_before_retry'] = df.reconcile(folder, 'W')
            assert details['reconcile_before_retry']['outcome'] == 'absent_from_current'
            # Осмотр candidate и артефактов, а затем безопасный повтор публикации.
            ps.validate_state(folder, candidate)
            saved = ps.save_state(folder, candidate)
            reload = cli(folder, 'load')
            assert reload['returncode'] == 0 and reload['result']['state']['revision'] == saved['revision']
            assert len(reload['result']['state']['decision']['events']) == 1
            assert df.reconcile(folder, 'W')['outcome'] == 'published'
            details['after_reconciled_retry'] = {'revision': saved['revision'], 'event_count': 1,
                                                'separate_load': reload['returncode']}
        details['passed'] = True
        results[name] = details
    return results


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    base = Path(sys.argv[1])
    base.mkdir(parents=True, exist_ok=False)
    results = run_scenarios(base)
    (base / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: {'passed': v['passed'], 'after': v.get('after_reconciled_retry', 'explicit recovery r2')}
                      for k, v in results.items()}, ensure_ascii=False, indent=2))
