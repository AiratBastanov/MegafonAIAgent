"""Local, standard-library arithmetic/checks only. No strategy generation or network.

Run from repository root with --output pointing to a new path inside demo-001.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
from pathlib import Path
from statistics import NormalDist


ROOT = Path(__file__).resolve().parents[2]
SPEC = "evidence/calculations/continuation-spec-v1.json"


def scoped(rel):
    path = (ROOT / rel).resolve()
    if Path(rel).is_absolute() or not path.is_relative_to(ROOT) or path == ROOT:
        raise ValueError("Path outside project")
    return path


def read(rel):
    return json.loads(scoped(rel).read_text(encoding="utf-8-sig"))


def ref(rel):
    return {"path": rel, "sha256": hashlib.sha256(scoped(rel).read_bytes()).hexdigest()}


def decimal(fraction, places="0.000001"):
    value = Decimal(fraction.numerator) / Decimal(fraction.denominator)
    return str(value.quantize(Decimal(places), rounding=ROUND_HALF_UP))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = scoped(args.output)
    if output.exists():
        raise FileExistsError("Output already exists; choose a new version")
    spec = read(SPEC)
    with scoped(spec["source_csv"]).open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    checks = []
    metric_columns = {
        "activation_pct": "activated", "retention_pct": "retained_d28",
        "paid_pct": "paid", "revenue_rub": "revenue_rub", "variable_cost_rub": "variable_cost_rub",
    }
    for key in ("saved_totals", "saved_segments"):
        result = read(spec[key])
        for group in result["groups"]:
            selected = [row for row in rows if all(row[k] == v for k, v in group["group"].items())]
            assert selected
            for metric, column in metric_columns.items():
                observed = group["metrics"][metric]
                if any(row[column] == "" for row in selected):
                    expected = None
                    passed = observed["value"] is None and observed["status"] == "missing"
                else:
                    expected = sum(Fraction(row[column]) for row in selected)
                    if metric.endswith("_pct"):
                        expected = expected * 100 / sum(int(row["eligible"]) for row in selected)
                    passed = Fraction(observed["value"]) == expected and observed["status"] == "ok"
                checks.append({"result": spec[key], "group": group["group"], "metric": metric,
                               "exact": str(expected) if expected is not None else None, "pass": passed})
    assert len(checks) == 30 and all(item["pass"] for item in checks)

    by_segment = {(row["period"], row["segment"]): row for row in rows}
    decomposition = []
    for column in ("retained_d28", "activated", "paid"):
        august = [row for row in rows if row["period"] == "2026-08"]
        september = [row for row in rows if row["period"] == "2026-09"]
        n_aug = sum(int(row["eligible"]) for row in august)
        n_sep = sum(int(row["eligible"]) for row in september)
        actual_aug = Fraction(sum(int(row[column]) for row in august), n_aug)
        actual_sep = Fraction(sum(int(row[column]) for row in september), n_sep)
        weighted = sum(Fraction(row["eligible"]) / n_sep *
                       Fraction(by_segment[("2026-08", row["segment"])][column]) /
                       Fraction(by_segment[("2026-08", row["segment"])]["eligible"])
                       for row in september)
        mix_change = sum((Fraction(row["eligible"]) / n_sep -
                          Fraction(by_segment[("2026-08", row["segment"])]["eligible"]) / n_aug) *
                         Fraction(by_segment[("2026-08", row["segment"])][column]) /
                         Fraction(by_segment[("2026-08", row["segment"])]["eligible"])
                         for row in september)
        assert weighted == actual_sep and mix_change == actual_sep - actual_aug
        decomposition.append({"metric": column, "august_pct": decimal(actual_aug * 100),
                              "september_pct": decimal(actual_sep * 100),
                              "standardized_august_rates_september_mix_pct": decimal(weighted * 100),
                              "mix_change_pp": decimal(mix_change * 100), "pass": True})

    econ_input, saved_econ = read(spec["economics_input"]), read(spec["saved_economics"])
    econ_checks = []
    for scenario in saved_econ["cohort_scenarios"]:
        expected = (Fraction(econ_input["revenue_rub"]) - Fraction(econ_input["paid"]) *
                    Fraction(scenario["variable_per_payer_rub"]) - Fraction(scenario["allocated_fixed_rub"]))
        passed = expected == Fraction(scenario["contribution_rub"])
        econ_checks.append({"kind": "cohort", "value_rub": str(expected), "pass": passed})
    pilot = econ_input["pilot_scenarios"]
    for scenario in saved_econ["pilot_scenarios"]:
        expected = (Fraction(pilot["eligible"]) * Fraction(scenario["additional_paid_rate"]) *
                    (Fraction(pilot["price_rub"]) - Fraction(pilot["variable_per_payer_rub"])) -
                    Fraction(pilot["allocated_incremental_cost_rub"]))
        econ_checks.append({"kind": "pilot", "value_rub": str(expected),
                            "pass": expected == Fraction(scenario["incremental_contribution_rub"])})
    assert len(econ_checks) == 7 and all(item["pass"] for item in econ_checks)

    a = spec["design_assumptions"]
    p0, p1 = float(a["baseline_d28"]), float(a["target_d28"])
    z_alpha = NormalDist().inv_cdf(1 - float(a["alpha_two_sided"]) / 2)
    z_power = NormalDist().inv_cdf(float(a["power"]))
    pbar = (p0 + p1) / 2
    numerator = z_alpha * math.sqrt(2 * pbar * (1 - pbar)) + z_power * math.sqrt(p0 * (1 - p0) + p1 * (1 - p1))
    n = math.ceil((numerator / (p1 - p0)) ** 2)
    assert math.sqrt(n) * (p1 - p0) >= numerator
    assert math.sqrt(n - 1) * (p1 - p0) < numerator
    pilot_total = Fraction(a["pilot_total_users"])
    pilot_treatment = pilot_total * Fraction(a["treatment_share"])
    pilot_control = pilot_total - pilot_treatment
    half_width = z_alpha * math.sqrt(p0 * (1 - p0) * (1 / float(pilot_treatment) + 1 / float(pilot_control)))
    flow = Fraction(a["recurring_arrivals_per_month"])
    days_month = Fraction(a["planning_days_per_month"])
    full_total = 2 * n
    sampling = {
        "method": "normal approximation; two-sided alpha; equal independent arms; no attrition",
        "formula_n_per_arm": "ceil((z_alpha*sqrt(2*pbar*(1-pbar))+z_power*sqrt(p0*(1-p0)+p1*(1-p1)))^2/(p1-p0)^2)",
        "z_alpha": format(z_alpha, ".9f"), "z_power": format(z_power, ".9f"),
        "required_per_arm": str(n), "required_total": str(full_total),
        "pilot_per_arm": str(pilot_treatment), "pilot_null_95pct_half_width_pp": format(half_width * 100, ".6f"),
        "full_recruitment_months": decimal(Fraction(full_total) / flow),
        "full_d28_total_days": decimal(Fraction(full_total) / flow * days_month + Fraction(a["outcome_maturation_days"])),
        "full_payment_total_days": decimal(Fraction(full_total) / flow * days_month + Fraction(a["payment_window_days"])),
        "pilot_d28_total_days": decimal(pilot_total / flow * days_month + Fraction(a["outcome_maturation_days"])),
        "pilot_payment_total_days": decimal(pilot_total / flow * days_month + Fraction(a["payment_window_days"])),
        "sample_size_inequality_crosscheck": True,
        "limitation": "Power is for superiority over zero at a true 10pp effect, not proof of an effect at least 10pp or adequate power for payments.",
    }
    margin = Fraction(a["illustrative_price_rub"]) - Fraction(a["illustrative_variable_per_payer_rub"])
    cost = Fraction(a["illustrative_total_incremental_test_cost_rub"])
    additional_payers_threshold = cost / margin
    econ_design = []
    for treated_n in (Fraction(100), pilot_treatment, Fraction(n)):
        threshold = cost / (treated_n * margin)
        assert threshold * treated_n == additional_payers_threshold
        econ_design.append({"treated_users": str(treated_n), "cost_rub": str(cost), "margin_rub_per_additional_payer": str(margin),
                           "break_even_paid_lift_exact": str(threshold), "break_even_paid_lift_pp": decimal(threshold * 100),
                           "minimum_integer_additional_payers": str(math.ceil(additional_payers_threshold)),
                           "integer_paid_lift_pp": decimal(Fraction(math.ceil(additional_payers_threshold)) / treated_n * 100),
                           "contribution_at_10pp_lift_rub": decimal(treated_n * Fraction(1, 10) * margin - cost, "0.01")})
    result = {
        "checked_at": datetime.now(timezone.utc).isoformat(), "synthetic": True,
        "tool": "project-local-check-continuation-v1", "method": "Fraction independent of analyze_table; explicit design assumptions; normal approximation",
        "inputs": [ref(SPEC)] + [ref(spec[k]) for k in ("source_csv", "saved_totals", "saved_segments", "saved_economics", "economics_input")],
        "script": ref("evidence/calculations/check-continuation-v1.py"),
        "metric_checks": checks, "decomposition": decomposition, "saved_economics_checks": econ_checks,
        "sampling": sampling, "experiment_economics": econ_design,
        "all_checks_passed": True,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"ok": True, "output": args.output, "metric_checks": len(checks), "economic_checks": len(econ_checks),
                      "sampling": sampling, "experiment_economics": econ_design}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
