"""Сценарии из файлов проекта. Без --write сверяет уже сохранённую версию."""
import argparse
import json
import math
from decimal import Decimal as D
from hashlib import sha256
from pathlib import Path
from statistics import NormalDist

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATHS = {
    "baseline": "inputs/baseline-v1.json",
    "assumptions": "inputs/scenarios-v1.json",
    "funnel": "calculations/funnel-v1.json",
}


def load(rel):
    return json.loads((ROOT / rel).read_bytes())


def sample(plan):
    p0 = float(plan["baseline"])
    difference = float(plan["minimum_difference"])
    p1 = p0 - difference
    pooled = (p0 + p1) / 2
    alpha = float(plan["alpha_familywise"]) / plan["two_sided_contrasts"]
    z = NormalDist().inv_cdf
    variance0 = 2 * pooled * (1 - pooled)
    variance1 = p0 * (1 - p0) + p1 * (1 - p1)
    n = math.ceil(((z(1 - alpha / 2) * math.sqrt(variance0) +
                    z(float(plan["power_per_contrast"])) * math.sqrt(variance1)) / difference) ** 2)
    assigned = math.ceil(n / D(plan["expected_observability"]))
    return {"observed_per_arm": n, "assigned_per_arm": assigned, "assigned_total": assigned * 3}


def forecast(baseline, inputs, funnel):
    indicators = baseline["indicators"]
    opening = indicators["connected_groups_december"][1]
    quarters = [group["metrics"] for group in funnel["groups"]]
    connections = sum(int(q["connected"]["value"]) for q in quarters)
    groups = opening + connections - inputs["family_departures"]
    owners = (indicators["connected_owners_december"][1] + inputs["owner_funnel"]["linked_two"]
              - inputs["owner_funnel"]["departures"])
    no_change = D(indicators["gross_profit_million_rub"][2]) * 10**6
    target = D(indicators["gross_profit_million_rub"][3]) * 10**6
    rate = D(baseline["gross_profit_per_incremental_paid_number_month_rub"])
    outputs = {}
    for key, s in inputs["scenarios"].items():
        cohorts = s["new_index_numbers"]
        ordinary = list(map(D, inputs["ordinary_survival_next_two"]))
        delta = list(map(D, s["survival_delta"]))
        monthly = []
        for month in range(12):
            # Считаются только следующие первое и второе платёжные окна.
            # Текущий уже оплачен. Прочим лагам приписан нулевой прирост.
            at_risk = [cohorts[month - lag] if month >= lag else 0 for lag in (1, 2)]
            paid_control = sum(n * q for n, q in zip(at_risk, ordinary))
            paid_signal = sum(n * (q + d) for n, q, d in zip(at_risk, ordinary, delta))
            monthly.append(dict(month=month + 1, new_index_numbers=cohorts[month],
                                eligible_at_lags=at_risk, paid_ordinary=paid_control,
                                paid_signal=paid_signal, incremental=paid_signal - paid_control))
        cumulative = D(0)
        period_rows = []
        for i, cost in enumerate(s["direct_budget_rub_by_quarter"]):
            paid = sum(row["incremental"] for row in monthly[3*i:3*i+3])
            contribution = paid * rate - cost
            cumulative += contribution
            period_rows.append(dict(quarter=i+1, incremental_months=paid, direct_rub=cost,
                                    net_rub=contribution, cumulative_rub=cumulative))
        cost = sum(s["direct_budget_rub_by_quarter"])
        base_activity = D(indicators["active_groups_december"][2]) / indicators["connected_groups_december"][2]
        extra_active = s["december_exposed_still_connected"] * D(s["incremental_active_probability"])
        q4 = quarters[-1]
        values = dict(gross_profit_million_rub=(no_change+cumulative)/10**6,
                      active_groups_december=groups * base_activity + extra_active,
                      connected_groups_december=groups, connected_owners_december=owners,
                      activation_q4_pct=D(q4["first14"]["value"]) * 100 / D(q4["created"]["value"]))
        outputs[key] = dict(monthly=monthly, quarters=period_rows, treated=sum(cohorts),
                            incremental_months=sum(v["incremental"] for v in monthly),
                            extra_gross_after_direct_rub=cumulative,
                            max_recoverable_investment_rub=max(0,cumulative),
                            required_paid_months=math.ceil((target-no_change+cost)/rate),
                            eligible_number_months=sum(sum(v["eligible_at_lags"]) for v in monthly),
                            december_activity_pct=D(values["active_groups_december"])*100/groups,
                            indicators=values, gaps={k:D(indicators[k][3])-v for k,v in values.items()})
    return {"synthetic": True,
            "basis_sha256": {k:sha256((ROOT/v).read_bytes()).hexdigest() for k,v in SOURCE_PATHS.items()},
            "scenarios": outputs, "sample_assumptions_only": sample(inputs["primary"])}


def run():
    return forecast(*(load(SOURCE_PATHS[k]) for k in ("baseline","assumptions","funnel")))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="создать новую версию результата")
    args = parser.parse_args()
    payload = json.dumps(run(), ensure_ascii=False, indent=2, default=str) + "\n"
    path = ROOT / "calculations/forecast-v1.json"
    if args.write:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
    elif json.loads(path.read_bytes()) != json.loads(payload):
        raise SystemExit("Расчёт отличается от сохранённой версии")
    print("Сценарии и численность эксперимента совпадают с сохранённым результатом.")
