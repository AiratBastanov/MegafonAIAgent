"""Собрать пакет из неизменённых первых ответов; не генерировать новые ответы."""
from pathlib import Path
import argparse
import json
import re

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent


def participant_text(condition, phase):
    folder = 'A' if condition == 'A' else 'B-ablation'
    text = (BASE / 'runs' / folder / phase / f'{phase}.md').read_text(encoding='utf-8')
    mapping = json.loads((BASE / 'workspace-map-v2.json').read_text(encoding='utf-8'))
    old = mapping['A' if condition == 'A' else 'B_ablation'].replace('\\', '/')
    target_root = f'../evaluation/task05/collected/{condition}'

    def replace(match):
        target = match.group(2).replace('\\', '/')
        if target.startswith(old + '/'):
            target = target_root + target[len(old):]
        elif target.startswith('../'):
            target = target_root + '/' + target[3:]
        return f'[{match.group(1)}]({target})'

    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', replace, text).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='docs/TASK05_REVIEW_PACKET.md')
    args = parser.parse_args()
    parts = ["""# TASK05 — полный пакет для проверки

**TASK05_EVAL_READY_WITH_EXECUTION_GAP.** Приведены все шесть первых полученных ответов выполненного A/B′ **ablation**, решающие источники, независимая оценка и исправления. Ordinary B — **NOT_RUN**: no-history host наследует Megafon AGENTS. FRESH_HOST_SAVE_RELOAD и соответствие официальному дополнительному брифу — **NOT_VERIFIED**. Это не ordinary-chat baseline и не human validation.

Замороженные [protocol v2](../evaluation/task05/protocol-v2.md), [manifest](../evaluation/task05/freeze-manifest-v2.json) и [prompts](../evaluation/task05/frozen-v2/prompts) созданы до ответов. A получил процедуры/утилиты/state; B′ — компетентное аналитическое задание, те же 54 предметных артефакта, обычные calculation tools и собственную историю/notes. Изоляция отдельных Temp workspaces процедурная, не ACL. Будущие события и evaluator notes участникам не передавались. [Полные условия и ограничения](TASK05_REPORT.md).

## Решающее первичное evidence

Числа — синтетический сценарий, не рынок или реальный эксперимент. Familiar — знакомый сценарий; variant с отзывом семи суток — новый вариант того же кейса, не второй независимый продукт.

| Значение/событие | Версия и координата | Проверяемый вывод |
|---|---|---|
| C3=3000, D3=600, E3=90, F3=600, G3=30000, H3=60000, I3=20 | [S002@2](../evaluation/task05/frozen-v2/B/materials/evidence/sources/S002/v2/original.xlsx), «Экономика»!C3:I3 | Вклад = 3000−600−90×600/60 = 1500; остаток при N=20 = 0; положительный с N=21 до неизвестных затрат. Setup 60000 отдельно. |
| 2 оплаты из 8 проб; 1 из 10 | Та же книга, «Воронка»!D3:D4 (пробы), F3:F4 (оплаты) | 25% и 10%. Новых входов нет, пересчёт не нужен. |
| 30→90 минут — уже учтённая поправка | [S005@1](../evaluation/task05/frozen-v2/B/materials/evidence/sources/S005/v1/original.txt), строки 1–5; [повтор Q1](../evaluation/task05/frozen-v2/events/q1/repeated-correction-v1.txt), строки 1–3 | Повтор без новой книги/измерения сам по себе не требует нового выбора владельца. |
| OWNER-01 разрешает учебную подготовку | [owner-instruction-v1](../evaluation/task05/frozen-v2/B/materials/inputs/owner-instruction-v1.md), абзацы об обязательствах и возврате к решению | Историю сохранять; реальный бюджет, внешний контакт и запуск не одобрены. |
| K-PROTOCOL/K-CAPABILITY: 17.11.2026 12:00 +03; M-TIME: план до 18.12.2026 12:00; G-FRESHNESS: 01.12.2026 12:00 | [context](../evaluation/task05/frozen-v2/B/context.md), commitments, metrics[M-TIME].window, conditions[G-FRESHNESS] | На Q1 19.12 12:00: 32, 1 и 18 суток. План не доказывает старт или завершённое наблюдение. K-BUDGET/K-VALUE без даты — blocked, не доказанная просрочка. |
| Familiar отзывает «без аккаунта»; variant — «семь суток» | [S001@1 extract](../evaluation/task05/frozen-v2/B/materials/evidence/sources/S001/v1/extract.json), physical-page:1/block:5; [familiar Q2](../evaluation/task05/frozen-v2/events/q2/familiar-withdrawal-v1.txt), [variant Q2](../evaluation/task05/frozen-v2/events/q2/variant-withdrawal-v1.txt), строки 2–4 | Withdrawal не доказывает противоположное. Правки продукта/сообщения/проверки различаются; отзыв срока затрагивает зависимость day23+7→day30. |
| Q3 повторяет поправку и сообщает переименование папки иллюстраций | [события Q3](../evaluation/task05/frozen-v2/events/q3), строки 1–3 | Новых обязательств/решений не создавать; законный review Q2 не снимать. |

Арифметика, даты, хеши и state проверены отдельно от прозы: [acceptance](../evaluation/task05/acceptance.json). S003/S004 — прежние публичные снимки TASK03, не новые live reads.

## Полные первые ответы

Текст не сокращён и не исправлен после оценки. Только targets Markdown-ссылок перенесены с Temp на сохранённые копии. Побайтовые originals/meta находятся в runs, крупные logs — в collected/A/logs и collected/B/logs. В Q1 обоим передано одинаковое техническое сообщение после отказа прав B′; предметных подсказок не было. Законченного ответа до помощи нет: полностью unassisted Q1 не измерен. Q2/Q3 получили только frozen requests. [Вмешательства](../evaluation/task05/interventions.json), [trace audit](../evaluation/task05/trace-audit.md).
"""]
    for phase in ('q1', 'q2', 'q3'):
        for condition in ('A', 'B'):
            folder = 'A' if condition == 'A' else 'B-ablation'
            label = 'A — репозиторий' if condition == 'A' else 'B′ — нейтральный пакет с inherited guidance'
            parts.append(f'### {phase.upper()} / {label}\n\n[Неизменённый raw response](../evaluation/task05/runs/{folder}/{phase}/{phase}.md).\n\n' + participant_text(condition, phase))
    review = (BASE / 'review-input/review.md').read_text(encoding='utf-8')
    review = re.sub(r'\[([^\]]+)\]\(([^)]+)\)',
                    lambda m: f'[{m.group(1)}](../evaluation/task05/review-input/{m.group(2)})', review)
    parts.append("""## Независимая оценка с причинами

Карта раскрыта после оценки: **R17=A, R42=B′**. Reviewer видел первичные материалы и полные обезличенные ответы без карты/оценок координатора. Порядок Q1/Q3 — B′→A, Q2 — A→B′. Ниже полный короткий вывод; все 73 evidence entries и причины каждого критерия — в его JSON. Указанное reviewer отсутствие времени относится к его слепому пакету; измеренные интервалы координатора приведены ниже.

""" + review.strip())
    parts.append("""## Сохранение и материальные исправления

Reviewer не видел native state A целиком. Координатор отдельно проверил loader: обе ветки загружаются в revision 5, OWNER-01 и четыре ID обязательств сохранены. Q3 сохраняет Q2 reviews/current_outputs и нужный owner review. Шесть raw responses совпадают с collected copies. B′ сохранил протоколы и последовательные handoffs; отсутствие private JSON schema A не снижало оценку. Canonical demo-001/demo-002 — revision 5/awaiting_decision. TASK04, unfinished TASK03 и прежние отчёты сохранены. [Acceptance](../evaluation/task05/acceptance.json).

| До | После и доказательство |
|---|---|
| План без старта получал ended_evidence_required | schedule_state отделён от window_state; observation требует evidence старта. [До](../evaluation/task05/controls-before.json), [после](../evaluation/task05/controls-final.json). |
| Повтор числа автоматически требовал нового выбора | Числовое изменение начинает аналитическую проверку без автоматического owner_required; новые существенные основания явно эскалируются. Подтверждённый повтор можно зарегистрировать без нового evidence_change. Независимый true сохраняется до choice. [Контроли](../evaluation/task05/controls-final.json), [процедура](../knowledge/procedures/decision-followup.md). |
| Первый fix оставлял flags после двух пересекающихся review | Сохранены происхождение flags и цепочка snapshots; оба порядка закрытия и независимый review проверены. [Первый FAIL](../evaluation/task05/code-review-v1.md), [финальный PASS](../evaluation/task05/code-review-final.md). |
| A/Q2: raw impact принят за calculation, AssertionError до save | Строгое распознавание typed/legacy impact. Marker-only и mixed calculation остаются conservative; explicit dependency links сохранены. [Исходный failure](../evaluation/task05/collected/A/logs/q2-prepare/stderr.txt), [review с ранним FAIL и 7 финальными PASS](../evaluation/task05/code-review-impact.md). |

Первые результаты не заменены. A самостоятельно восстановился на frozen коде, без содержательной подсказки координатора. Финальные **85 regression tests PASS** — [log](../evaluation/task05/observations/regression-final-03/stderr.txt), [команда/время](../evaluation/task05/observations/regression-final-03/result.json). Исправленная версия закреплена [manifest](../evaluation/task05/implementation-final-02.json). Это **correction checks**, не новая сравнительная пара; качество после содержательной помощи и ускорение новой версии не измерены.

## Ресурсы и следующий шаг

Наблюдаемая подготовка — 805.7 s, включая нейтральную нормализацию. От первого до последнего captured subprocess шага: A — 657.9 / 915.2 / 274.6 s; B′ — 670.5 / 404.7 / 132.5 s. Непересекающиеся интервалы внутри A — 1847.7 s, B′ — 1207.7 s; объединение обоих — 1861.1 s. Пара шла одновременно, totals не складываются. Bootstrap/final delivery могут лежать вне границ; retries и reasoning gaps внутри. Captured commands 54/26 — не все host tool calls. [Ресурсы](../evaluation/task05/resource-accounting.json).

Review: 702.8 s от первого успешного UTC reading до завершения оценки; более ранняя граница неизвестна. [Метаданные](../evaluation/task05/review-input/review-meta.json). Fixes, grading и оформление пересекаются с другими интервалами. Tokens, charges, exact model/settings, прежняя отдельная стоимость r3 и активное человеческое время неизвестны. Общий cutoff и журнал — [completion observation](../evaluation/task05/completion-observation.json).

Ничья 28/28 и 0 найденных critical errors относится только к этим запросам и шкале. Блайндинг несовершенен, shared-model ограничения и отсутствие человеческой калибровки сохраняются; выборка мала. Смыслового/скоростного преимущества над обычным ассистентом не доказано. Подтверждены проверяемое сохранение A и полезный readable handoff B′.

Следующий ограниченный шаг — новая ordinary A/B пара по [handoff](../evaluation/task05/README.md), после подтверждения отсутствия project guidance у B. Отдельно остаются **FRESH_HOST_SAVE_RELOAD — NOT_VERIFIED** на подлинном checkpoint TASK03 и **official-brief conformity — NOT_VERIFIED**. [Submission readiness](SUBMISSION_READINESS.md) не означает выполненные скриншоты, видео, публикацию или сдачу.
""")
    destination = ROOT / args.output
    with destination.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write('\n\n'.join(parts).rstrip() + '\n')
    print(json.dumps({'path': str(destination), 'bytes': destination.stat().st_size,
                      'complete_first_responses': 6}, ensure_ascii=False))


if __name__ == '__main__':
    main()
