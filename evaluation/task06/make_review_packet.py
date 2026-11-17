"""Extract the actual final demo artifacts into a self-contained review document."""
from pathlib import Path
import hashlib
import json
ROOT=Path(__file__).resolve().parents[2]
p=ROOT/'projects/task06-rehearsal'
state=json.loads((p/'state/current.json').read_text(encoding='utf-8'))
lines=['# TASK06 — содержательный пакет независимого ревью','',
'**TASK06_LOCAL_PACKAGE_WITH_GAPS.** Локальный кандидат с отдельной учебной репетицией. Независимое продолжение NOT_VERIFIED, ordinary baseline NOT_RUN, official-brief conformity NOT_VERIFIED, VIDEO_NOT_RECORDED; публикация/доступ/сдача не подтверждены. Следующие тексты извлечены из фактических файлов, а не восстановлены как исторические ответы.',
'','## Решающее evidence','',
'- Учебный PDF S001@1 физическая страница 1, строки 4–8: исходящая ссылка/ручной отзыв; 2 GB на файл, семь дней, получатель без аккаунта; входящей загрузки, пароля, SSO и аудита нет. Описание не равно приёмке.',
'- PDF физическая страница 2, строки 2–4: paid pilot в sales означает интерес. XLSX S002@1 Воронка D3/F3=8/2, D4/E4/F4=10/8/1: фактические для fixture первые оплаты 2/8=25% и 1/10=10%. Не реальные клиенты/спрос.',
'- S002@2 Экономика C3:I3: 3000,600,90,600,30000,60000,20. Вклад 3000−600−90×600/60=1500 RUB/организацию/месяц; при 20 остаток 0 до неизвестных затрат; строго положительный с 21. Исходная v1 имела 30 минут, вклад 2100 и остаток 12000.',
'- Реально прочитаны официальные Dropbox create-dropbox-transfer и create-file-request 16.11.2026; выдержка S003@1 T1/T2. Функциональные альтернативы не доказывают применимость/спрос.',
'- Обе версии: 16 независимых Fraction/OOXML arithmetic checks и 39 fidelity checks PASS. Current state r'+str(state['revision'])+', '+state['stage']+', decision='+state['decision']['status']+', принятых решений '+str(len(state['decision']['history']))+'.',
'- Пауза r1 захвачена 15:26:21.569715 UTC, первый дальнейший расчёт 15:26:22.449953 UTC. Handoff 46/46 SHA; поздние результаты не переданы. Последующие результаты принадлежат прежнему координатору в другой копии, не fresh host.',
'- TASK05 frozen-v2 PRE-FIX: A/B′ ablation 28/28 у обоих, найденных critical answer errors 0. A 1847.658542 с против B′ 1207.712457 с. Преимущество обычному ассистенту не установлено. 85 PASS последующих исправлений не новый benchmark.',
'- В TASK06 новый offline setup из распаковки prep1, pip check и load r6 прошли. Точные финальные ZIP/extracted checks сохраняются снаружи, в dist/validation-rc1. Подробная первая команда/вывод не подменяют LLM-run.',
'','## Существенные ошибки и вмешательства','',
'Сетевой pip отклонён WinError10013: использованы существующие cached wheels с pins/RECORD/SHA, настройки не менялись. Ошибка draft provenance отклонена validator до save и исправлена новым draft. Исправлены timestamp/offset и направление метаданных raw→scenario; r5 synthetic=False исправлено новой r6. Старые данные и ошибки сохранены. Первый export WinError32 исправлен записью PDF из памяти. PS capture helper запрещён execution policy; bypass не применялся. Отдельный reviewer подтвердил исправление synthetic metadata и не оставил материальных findings в проверенном объёме. Human review/approval не было.',
'','Репетиция 15:23:45.600681–15:35:50.714355 UTC = 725.113674 с (wall interval с паузами). Подготовка/экспорт/review/упаковка отдельны и могут пересекаться. Tokens, charges, точная модель/settings, активное время человека неизвестны. Фактический manager prompt и correction prompt ниже — авторские учебные prompts TASK06, не стенограмма владельца бизнеса.']
for heading,relative in [('Исходный запрос','inputs/manager-request-v1.txt'),('Коррекция','inputs/correction-request-v2.txt'),
    ('Ситуация v2','outputs/v2/situation.md'),('Варианты v2','outputs/v2/options.md'),
    ('Продуктовая стратегия v2','outputs/v2/product-strategy.md'),('Коммуникационная стратегия v2','outputs/v2/communication-strategy.md'),
    ('План проверки v2','outputs/v2/validation-plan.md'),('Разбор коррекции','evidence/correction-review-v2.md')]:
    source=p/relative
    lines+=['',f'## {heading}','',f'Источник: `projects/task06-rehearsal/{relative}`; SHA-256 `{hashlib.sha256(source.read_bytes()).hexdigest()}`.','',source.read_text(encoding='utf-8')]
lines+=['','## Проверяемый следующий шаг','',
'В новой пустой папке распаковать evaluation/task06/continuation-checkpoint.zip; установить новую venv по RUNTIME.md. В новом независимом разрешённом Codex-контексте дать только: «Продолжи анализ проекта task06-rehearsal по сохранённому состоянию.» Ожидаются собственный содержательный анализ, новая valid revision и последующий отдельный load; исходные hashes не менять. Не передавать этот packet в такой контекст. Нужны настоящий video segment, дополнительные официальный brief/сверка, доступ жюри и подтверждение сдачи. Ключи не запрашиваются.']
# Embedded source-relative links would be misleading in the standalone packet: keep their labels and literal target text.
import re
text='\n'.join(lines)+'\n'
text=re.sub(r'\[([^\]]+)\]\((\.\.?/[^)]+|calculations/[^)]+|correction-impact-v1.json)\)',r'\1 (путь в исходном документе: `\2`)',text)
with (ROOT/'docs/TASK06_REVIEW_PACKET.md').open('x',encoding='utf-8') as f:f.write(text)
print(json.dumps({'packet':'docs/TASK06_REVIEW_PACKET.md','revision':state['revision'],'characters':len(text)}))
