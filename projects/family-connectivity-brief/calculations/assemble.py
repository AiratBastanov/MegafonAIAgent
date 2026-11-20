"""Собрать пять разделов из одной версии аналитических документов и сверить таблицу с расчётом."""
import argparse
import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("version", help="каталог результатов, например v1")
parser.add_argument("--write", action="store_true")
args = parser.parse_args()
if not (args.version.startswith("v") and args.version[1:].isdigit()):
    parser.error("нужен номер версии vN")
folder = ROOT / "outputs" / args.version


def body(name):
    lines = (folder / name).read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("# ")
    return "\n".join(lines[1:]).strip()


def section(document, start, end):
    return document.split(f"<!-- {start} -->", 1)[1].split(f"<!-- {end} -->", 1)[0].strip()


def number(cell):
    return Decimal(cell.replace(" ", "").replace(",", ".").replace("п.п.", "").strip())


product = body("product-strategy.md")
validation = body("validation-plan.md")
options = body("options.md")
baseline = json.loads((ROOT / "inputs/baseline-v1.json").read_bytes())
scenarios = json.loads((ROOT / "calculations/forecast-v1.json").read_bytes())["scenarios"]
rows = options.split("| Показатель |", 1)[1].split("\n\n", 1)[0].splitlines()[2:]
assert len(rows) == len(baseline["indicators"]) == 5
for (indicator, initial), row in zip(baseline["indicators"].items(), rows, strict=True):
    cells = [v.strip() for v in row.strip("|").split("|")]
    assert [number(v) for v in cells[1:5]] == initial
    assert [number(v) for v in cells[5:7]] == [Decimal(scenarios[v]["indicators"][indicator]) for v in ("main","weak")]
    assert [number(v) for v in cells[7].split("/")] == [Decimal(scenarios[v]["gaps"][indicator]) for v in ("main","weak")]

parts = [
    "# Семейная связь до исчерпания пакета",
    section(product, "lead", "service"),
    "## 1. Клиент и его проблема", body("situation.md"),
    "## 2. Предложение и путь к клиенту", section(product, "service", "value"),
    "### Как говорить с семьёй", body("communication-strategy.md"),
    "## 3. Польза для клиента и прибыль оператора", section(validation, "decision-test", "detail"),
    section(product, "value", "resources"),
    "## 4. Стратегический выбор и план по кварталам", options,
    "## 5. Ресурсы, риски и решение руководителя", section(product, "resources", "end"),
    "### Условия остановки и возобновления", validation.split("### Правила принятия решений",1)[1].split("<!-- end -->",1)[0].strip(),
    "К 31 марта просим руководителя решить, финансировать ли указанный пилот на одном тарифе и по какой смете. К 30 июня руководитель с финансами получит журнал исполнения и вреда, фактический недельный набор и недостающую выборку. По ним можно остановить, исправить или продлить испытание. Для массового запуска потребуются подтверждённые польза и экономика. [Метрики и первичные журналы для решения](validation-plan.md) · [Происхождение брифа и выполненные проверки](../../evidence/verification.md)",
]
text = "\n\n".join(parts) + "\n"
target = folder / "strategy.md"
if args.write:
    with target.open("x",encoding="utf-8",newline="\n") as stream:
        stream.write(text)
elif text != target.read_text(encoding="utf-8"):
    raise SystemExit("Сводная стратегия отличается от проверенных составляющих")
print("Пять разделов собраны из одной версии. Все 40 чисел основной таблицы сверены с входами и расчётами.")
