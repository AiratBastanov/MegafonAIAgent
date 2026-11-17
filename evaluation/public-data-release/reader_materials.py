"""Mechanical consolidation and hashes; analytical wording is supplied by the coordinator."""
from pathlib import Path
import hashlib
import json
import os
import re
from urllib.parse import unquote

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'evaluation/task07/demo-workspace/projects/task06-rehearsal'
TARGET=ROOT/'submission/strategies'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def relocate(text, source, output):
    def replace(m):
        target=m.group(1)
        if ':' in target or target.startswith('#'):
            return m.group(0)
        actual=(source.parent/unquote(target)).resolve()
        return ']('+Path(os.path.relpath(actual,output.parent)).as_posix()+')'
    return re.sub(r'\]\(([^)\n]+)\)',replace,text)

old=BASE/'outputs/v2/communication-strategy.md'
target=TARGET/'COMMUNICATION.md'
text=relocate(old.read_text(encoding='utf-8'),old,target)
text=text.replace('# Коммуникационная стратегия\n', '# Коммуникационная стратегия RelayBox\n',1)
intro='''
**Текущее предложение: не приглашать участников и не обещать экономию до пересмотра бюджета, технической приёмки и отдельного решения.**

Это самостоятельная читательская версия текущего результата. Клиенты, расходы, выбор и событие учебные; реальных продаж и разрешённого пилота нет. Включены текущие уточнения и ранее определённые аудитория, барьер, доказательства, роли каналов и ответы на возражения. Канонические версии не изменены. [Текущий пересмотр](../../evaluation/task07/demo-workspace/projects/task06-rehearsal/outputs/v4/communication-strategy.md), [наследуемые разделы](../../evaluation/task07/demo-workspace/projects/task06-rehearsal/outputs/v2/communication-strategy.md).

Рост поддержки с 30 до 90 минут относится к поставщику, а не к клиентской экономии. При цене 3 000 ₽, инфраструктуре 600 ₽ и часе помощи 600 ₽ частичный вклад уменьшается с 2 100 до 1 500 ₽. При двадцати организациях и фиксированных 30 000 ₽ частичный остаток становится нулём вместо 12 000 ₽ — до неизвестных привлечения и налогов. Это сценарий, не прибыль и не измеренный убыток бизнеса. [Расчёт](../../evaluation/task07/demo-workspace/projects/task06-rehearsal/evidence/calculations/support90-v1.json).

Внутреннее сообщение команды: «Учебное допущение поддержки выросло втрое; частичный остаток при 20 организациях стал нулевым. Допуск приостановлен до полной сметы и нового решения». Исходный симулированный выбор остаётся в истории, обязательства не выполнены.

'''
text=text.replace('\n\n', '\n\n'+intro,1)
text=text.replace('Текст согласован с условным выбором продуктовой стратегии.', 'Текст согласован с текущим предложением приостановить допуск в продуктовой стратегии.')
text=text.replace('[продуктовая стратегия](../../evaluation/task07/demo-workspace/projects/task06-rehearsal/outputs/v2/product-strategy.md)',
                  '[продуктовая стратегия](PRODUCT.md)')
text=text.replace('outputs/v2/validation-plan.md','outputs/v4/validation-plan.md')
plan='''
## Совместная проверка продукта и сообщения

После допуска сравниваются 12 организаций, по четыре задачи за 28 дней: две каждым способом, порядок случайный; контроль — лучший разрешённый способ с реальным тарифом клиента. Предлагаемые совместные пороги: 9 из 12 экономят не менее пяти клиентских минут при завершении не хуже контроля; ценность до платы не менее 6 000 ₽/месяц у 6 из 12, включая минимум трёх повторных плательщиков; минимум четыре первые и три повторные оплаты по 3 000 ₽, повторы не менее 60% первых.

Первое окно оплаты — семь дней; повтор — через календарный месяц после первой оплаты и ещё семь дней. Итог ждёт окон всех впервые оплативших и месячного наблюдения частоты у всех 12, включая неплательщиков. Пороги предложены для согласования, а не наблюдались. Нежелательный доступ, потеря файлов и ошибки отзыва требуют остановки. Пропуски, несопоставимый контроль и недостаточная точность означают неопределённость. Сильнее обещать продукт ради хорошей реакции запрещено.

[Полный согласованный план](../../evaluation/task07/demo-workspace/projects/task06-rehearsal/outputs/v4/validation-plan.md) раскрывает определения ценности, помощь команды, вред, условия закрытия и отдельное решение о масштабе.

'''
text=text.replace('## Примечания',plan+'## Примечания',1)
text+='\n[Продуктовая стратегия](PRODUCT.md) · [Происхождение читательских версий](SOURCES.md).\n'
with target.open('x',encoding='utf-8') as f:
    f.write(text)
sources=[BASE/'outputs/v4'/name for name in ('product-strategy.md','communication-strategy.md','options.md','situation.md','validation-plan.md')]
sources+=[old,BASE/'evidence/strategy-evidence-register-v2.md',BASE/'evidence/calculations/support90-v1.json']
manifest={'canonical_sources':[{ 'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)} for p in sources],
          'reader_documents':[{ 'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)} for p in (TARGET/'PRODUCT.md',target)],
          'scope':'Reader consolidation only; no canonical state or output mutation'}
with (TARGET/'sources.json').open('x',encoding='utf-8') as f:
    json.dump(manifest,f,ensure_ascii=False,indent=2)
with (TARGET/'SOURCES.md').open('x',encoding='utf-8') as f:
    f.write('# Происхождение читательских стратегий\n\nЭто объяснительное изложение для жюри, не точные цитаты и не новые бизнес-решения.\n\n')
    f.write('Продуктовая стратегия объединяет текущую стратегию, ситуацию, варианты и план проверки. Коммуникационная включает текущий пересмотр и разделы предыдущей полной версии: аудиторию, барьер, подтверждения, роли каналов и возражения. Текущая приостановка допуска имеет приоритет перед прежней условной готовностью к проверке.\n\n')
    for p in sources:
        f.write('- ['+p.stem.replace('-',' ')+' — '+p.parent.name+']('+Path(os.path.relpath(p,TARGET)).as_posix()+').\n')
    f.write('\n[Точный реестр исходных и читательских файлов с SHA256](sources.json). Исходные файлы и сохранённые решения не переписаны.\n')
print('Consolidated communication strategy; canonical sources hashed without mutation.')
