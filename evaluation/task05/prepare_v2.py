"""Убирает прежние evaluator notes; чистый rebase одинаковых бизнес-фактов.

v1 сохраняется как неисполненный подготовительный пакет. Ответов здесь нет.
"""
import copy
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path
from prepare import ROOT, BASE, write, sha, manifest, now, copy_file, neutral_context
import project_state as ps
import decision_followup as df


def main():
    start, counter = now(), time.monotonic()
    out = BASE/'frozen-v2'
    if out.exists():
        raise SystemExit('frozen-v2 уже существует')
    old = BASE/'frozen-v1'
    source = old/'A/branches/familiar/projects/task04-followup'
    original = ps.load_state(source)
    excluded = {'REVIEW-v1', 'REVIEW-v2', 'RUN-OBSERVATION-v2', 'ACTIONS-v1', 'ORIGIN-STATE'}
    base = copy.deepcopy(original)
    base['artifacts'] = [a for a in base['artifacts'] if a['id'] not in excluded]
    assert not any(e['artifact_id'] in excluded for c in base['claims'] for e in c['evidence'])
    choice = copy.deepcopy(original['decision']['events'][0])
    choice.pop('fingerprint', None)
    for key in ('history','events','commitments','reviews'):
        base['decision'][key] = []
    base['decision'].update(status='awaiting_decision', owner='unassigned')
    base['evaluation']['task05_origin'] = {'state_sha256': original['state_sha256'], 'revision':3,
        'normalization': 'Сохранены бизнес-факты/определения/инструкция/исторические стратегии; исключены evaluator notes и технические журналы; basis перепривязан к чистой r1'}
    for branch in ('familiar','variant'):
        project = out/'A/branches'/branch/'projects/task04-followup'
        for a in base['artifacts']:
            copy_file(source/a['path'], project/a['path'])
            copy_file(source/a['path'], out/'B/materials'/a['path'])
        write(project/'task05-branch.md', '# Изолированная ветка '+branch+'\n\nЧистый пакет фактов r3 TASK04 с техническим rebase. Не содержит поздних ответов или evaluator notes.\n')
        saved = ps.save_state(project, base)
        candidate, changed = df.apply_event(project, saved, choice)
        assert changed
        saved = ps.save_state(project, candidate)
        ps.load_state(project)
        if branch == 'familiar':
            context = neutral_context(saved)
    for name in ('scripts','knowledge'):
        shutil.copytree(old/'A'/name, out/'A'/name)
    copy_file(old/'A/AGENTS.md', out/'A/AGENTS.md')
    for name in ('A','B'):
        for rel in ('RUNTIME.md','capture.py','inbox/q1/repeated-correction-v1.txt'):
            copy_file(old/name/rel, out/name/rel)
        write(out/name/'context.md', context)
    for name in ('events','prompts'):
        shutil.copytree(old/name, out/name)
    copy_file(old/'origin.json', out/'origin-r3.json')
    write(out/'normalization.json', {'excluded_artifact_ids':sorted(excluded),
        'reason':'исключение evaluator notes и технических журналов из обоих participant packages до измерения',
        'native_revision':2,'history_choice':'OWNER-01, прежние option/reason/grounds и 4 commitments; новый технический basis',
        'prior_v1':'NOT_RUN; сохранён', 'same_business_facts':True})
    temp_root = Path(tempfile.mkdtemp(prefix='megafon-task05-clean-'))
    ancestry = [{'path':str(p/'AGENTS.md'),'exists':(p/'AGENTS.md').exists()} for p in [temp_root,*temp_root.parents]]
    assert not any(x['exists'] for x in ancestry)
    for name in ('A','B'):
        shutil.copytree(out/name,temp_root/name)
    write(BASE/'workspace-map-v2.json', {'A':str(temp_root/'A'),'B_ablation':str(temp_root/'B'),
        'ordinary_B':'NOT_RUN','ancestry':ancestry,'isolation':'procedural; общий sandbox'})
    write(BASE/'protocol-v2.md', (BASE/'protocol-v1.md').read_text(encoding='utf-8') +
        '\n## Уточнение v2 до измерения\n\nРабочий freeze — frozen-v2, manifest-v2. '
        'Исходная предметная история TASK04 r3 перенесена в чистые r1–2. Старые evaluator notes, run/action logs '
        'и origin-state, содержащий их реестр, исключены. Исторические стратегии/расчёты/исправления и OWNER-01 '
        'остаются входами; технический basis и время публикации созданы заново, не выдаются за оригинальный r3. '
        'frozen-v1 не запускался; сохранён для аудита подготовки. Ожидания и rubric v1 не менялись.\n')
    write(BASE/'prepare-v2-observation.json', {'started_at':start,'ended_at':now(),'elapsed_seconds':time.monotonic()-counter,
        'normalization_cost':'в этом интервале копирование, фильтрация и 4 save + 4 load/validation; полный труд подготовки учитывается отдельно'})
    files = {p.relative_to(BASE).as_posix():sha(p) for p in [BASE/'protocol-v2.md',BASE/'rubric-v1.json',BASE/'expectations-v1.json',BASE/'prepare_v2.py',BASE/'implementation-before.json']}
    files.update({'frozen-v2/'+k:v for k,v in manifest(out).items()})
    write(BASE/'freeze-manifest-v2.json',{'frozen_at':now(),'files':files})
    print(json.dumps({'workspaces':str(temp_root),'frozen_files':len(files),'native_revision':2},ensure_ascii=False))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
