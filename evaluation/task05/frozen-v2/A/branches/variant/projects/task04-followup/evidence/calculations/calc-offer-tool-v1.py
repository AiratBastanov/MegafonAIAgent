"""Явные сценарные формулы demo-002; не выбор стратегии и не Excel engine."""
import argparse
from datetime import datetime,timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.import_materials import scoped,sha256,json_bytes,write_new


def run(project,raw_metrics,assumptions,output):
    project=Path(project);path=scoped(project,raw_metrics);plan=scoped(project,assumptions)
    data=json.loads(path.read_text(encoding="utf-8"));params=json.loads(plan.read_text(encoding="utf-8"))
    if data.get("tool")!="analyze_table" or len(data["groups"])!=1:raise ValueError("Нужен один явно заданный экономический сценарий")
    origin=data["source"];meta=json.loads(scoped(project,f"evidence/sources/{origin['id']}/v{origin['version']}/source.json").read_text(encoding="utf-8"))
    if sha256(scoped(project,data["input"]["path"]).read_bytes())!=data["input"]["sha256"] or data["input"]["sha256"]!=meta["input_sha256"]:
        raise ValueError("Исходная книга изменилась")
    if sha256(scoped(project,data["spec"]["path"]).read_bytes())!=data["spec"]["sha256"]:raise ValueError("Спецификация изменилась")
    expected={"price":"RUB/account/month","infra":"RUB/account/month","support_minutes":"minutes/account/month",
              "hourly_cost":"RUB/hour","fixed":"RUB/month","setup":"RUB","accounts":"accounts"}
    raw={}
    for name,unit in expected.items():
        metric=data["groups"][0]["metrics"][name]
        if metric["status"]!="ok" or metric["unit"]!=unit:raise ValueError("Неизвестное значение или единица: "+name)
        raw[name]=Decimal(metric["value"])
    def scenario(minutes,accounts):
        support=minutes*raw["hourly_cost"]/Decimal(60)
        margin=raw["price"]-raw["infra"]-support
        surplus=accounts*margin-raw["fixed"]
        return {"support_minutes":str(minutes),"accounts":str(accounts),"support_rub_per_account_month":str(support),
                "margin_rub_per_account_month":str(margin),"surplus_before_unknown_costs_rub_month":str(surplus),
                "min_accounts_nonnegative":int((raw["fixed"]/margin).to_integral_value(rounding=ROUND_CEILING)) if margin>0 else None,
                "min_accounts_positive":int((raw["fixed"]/margin).to_integral_value(rounding=ROUND_FLOOR))+1 if margin>0 else None,
                "conditional_setup_payback_months":str(raw["setup"]/surplus) if surplus>0 else None}
    scenarios=[scenario(Decimal(m),Decimal(n)) for m in params["support_minutes_scenarios"] for n in params["accounts_scenarios"]]
    result={"calculated_at":datetime.now(timezone.utc).isoformat(),"tool":"calc_offer_scenarios","tool_version":"1",
            "synthetic":bool(data["synthetic"] or params["synthetic"]),"source":origin,
            "input":data["input"],"raw_metrics":{"path":raw_metrics,"sha256":sha256(path.read_bytes())},
            "assumptions":{"path":assumptions,"sha256":sha256(plan.read_bytes())},
            "tool_sha256":sha256(Path(__file__).read_bytes()),"provenance":data.get("provenance"),
            "formulas":{"support":"minutes * RUB_per_hour / 60","margin":"price - infra - support",
                        "surplus":"paying_accounts * margin - avoidable_fixed","nonnegative":"ceil(fixed/margin) if margin>0",
                        "positive":"floor(fixed/margin)+1 if margin>0","payback":"setup/surplus if surplus>0"},
            "base":scenario(raw["support_minutes"],raw["accounts"]),"scenarios":scenarios,
            "limitations":params["limitations"],"reproduce":{"raw_metrics":raw_metrics,"assumptions":assumptions}}
    write_new(scoped(project,output,must_exist=False),json_bytes(result));return result


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--project",required=True);p.add_argument("--raw-metrics",required=True);p.add_argument("--assumptions",required=True);p.add_argument("--output",required=True)
    a=p.parse_args();r=run(a.project,a.raw_metrics,a.assumptions,a.output);print(json.dumps({"base":r["base"],"scenarios":len(r["scenarios"])}))
