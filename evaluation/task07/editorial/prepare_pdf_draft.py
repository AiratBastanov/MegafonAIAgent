"""Derive a separate editorial version with an explicit gate and logical pages."""
from pathlib import Path

folder = Path(__file__).resolve().parent
source = folder / 'Описание-проекта-черновик.md'
target = folder / 'Описание-проекта-черновик-2.md'
if target.exists():
    raise FileExistsError(target)
text = source.read_text(encoding='utf-8')
old = 'Менее пяти успешных завершений из шести либо медианное снижение времени менее 20% без сокращения ошибок не поддерживает гипотезу.'
new = 'Предлагаемые условия перехода: не менее пяти успешных завершений из шести, медианное снижение времени не менее 20%, число ошибок не растёт. Невыполнение любого условия не поддерживает переход к следующему этапу.'
assert text.count(old) == 1
text = text.replace(old, new)
for heading in ('## Четыре варианта', '## Что меняет', '## Как агент', '## Средства'):
    assert text.count(heading) == 1
    text = text.replace(heading, '<!-- PAGE -->\n\n' + heading)
needle = '## Как агент работает и помнит задачу'
text = text.replace('<!-- PAGE -->\n\n' + needle,
    '[[SCREENSHOT: Симулированный выбор, обязательство и требование пересмотра после изменения поддержки. Кадр должен содержать непустую историю решения.]]\n\n<!-- PAGE -->\n\n' + needle)
needle = 'Действующие инструкции включают:'
text = text.replace(needle,
    '[[SCREENSHOT: Настоящий новый контекст: собственный аналитический результат и успешное сохранение. Если продолжение не выполнено, вместо изображения честно описать границу.]]\n\n' + needle)
with target.open('x', encoding='utf-8') as stream:
    stream.write(text)
print(target.name)
