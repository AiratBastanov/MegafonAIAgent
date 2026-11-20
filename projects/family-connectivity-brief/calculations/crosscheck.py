"""Независимая сверка по исходным CSV и когортам, без импорта model.py."""
import csv
import json
import math
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
read = lambda rel: json.loads((ROOT / rel).read_bytes())
b = read("inputs/baseline-v1.json")
s = read("inputs/scenarios-v1.json")
r = read("calculations/forecast-v1.json")
with (ROOT / "inputs/funnel-v1.csv").open(encoding="utf-8", newline="") as h:
    rows = list(csv.DictReader(h))
assert len({(row["quarter"], row["channel"]) for row in rows}) == len(rows) == 8
assert all(0 <= int(x["first14"]) <= int(x["connected"]) <= int(x["created"]) <= int(x["households"]) for x in rows)
family = 6500 + sum(int(x["connected"]) for x in rows) - s["family_departures"]
q4 = [x for x in rows if x["quarter"] == "Q4"]
activation = F(100*sum(int(x["first14"]) for x in q4),sum(int(x["created"]) for x in q4))
owners = 800 + s["owner_funnel"]["linked_two"] - s["owner_funnel"]["departures"]
assert (family,owners,activation) == (8000,1000,45)
assert (12000-6500,12000-8000,(285-279)*10**6//500) == (5500,4000,12000)
for key, expected in r["scenarios"].items():
    scenario = s["scenarios"][key]
    earned = [F(0)] * 12
    exposures = 0
    for start, count in enumerate(scenario["new_index_numbers"]):
        for _ in range(count):  # независимое разложение «один номер × доступные месяцы»
            for lag, delta in enumerate(scenario["survival_delta"],1):
                if start + lag < 12:
                    earned[start+lag] += F(delta)
                    exposures += 1
    assert earned == [F(v["incremental"]) for v in expected["monthly"]]
    assert exposures == expected["eligible_number_months"]
    net = F(0)
    for q, cost in enumerate(scenario["direct_budget_rub_by_quarter"]):
        net += 500 * sum(earned[q*3:q*3+3]) - cost
        assert net == F(expected["quarters"][q]["cumulative_rub"])
    costs = sum(scenario["direct_budget_rub_by_quarter"])
    threshold = expected["required_paid_months"]
    assert 500*(threshold-1)-costs < 6000000 <= 500*threshold-costs
    extra = scenario["december_exposed_still_connected"]*F(scenario["incremental_active_probability"])
    indicators = [279+net/10**6,F(family*5,8)+extra,family,owners,activation]
    for (name, conditions), value in zip(b["indicators"].items(), indicators, strict=True):
        assert value == F(expected["indicators"][name])
        assert conditions[-1]-value == F(expected["gaps"][name])
    assert max(0,net) == F(expected["max_recoverable_investment_rub"])
n = math.ceil(((2.2414027276*math.sqrt(2*.175*.825)+.8416212336*math.sqrt(.2*.8+.15*.85))/.05)**2)
assert r["sample_assumptions_only"] == dict(observed_per_arm=n,assigned_per_arm=math.ceil(n/.95),assigned_total=3*math.ceil(n/.95))
print("Сверены 24 помесячные разницы, 8 квартальных итогов, 10 прогнозов и разрывов, оба порога и расчёт набора.")
