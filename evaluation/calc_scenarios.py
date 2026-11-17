"""Явные сценарии из JSON: арифметика, без выбора стратегии."""
import argparse
import hashlib
import json
from decimal import Decimal
from pathlib import Path
from datetime import datetime, timezone


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();data=json.loads(a.input.read_text(encoding='utf-8')); D=Decimal
    cohort=[]
    for v in data['variable_per_payer_rub_scenarios']:
        for f in data['allocated_fixed_rub_scenarios']:
            value=D(data['revenue_rub'])-D(data['paid'])*D(v)-D(f)
            cohort.append({'variable_per_payer_rub':v,'allocated_fixed_rub':f,'contribution_rub':str(value)})
    q=data['pilot_scenarios']; margin=D(q['price_rub'])-D(q['variable_per_payer_rub']); pilot=[]
    for rate in q['additional_paid_rate']:
        added=D(q['eligible'])*D(rate)
        pilot.append({'additional_paid_rate':rate,'additional_payers':str(added),'incremental_contribution_rub':str(added*margin-D(q['allocated_incremental_cost_rub']))})
    result={'calculated_at':datetime.now(timezone.utc).isoformat(),'synthetic':True,'kind':'scenario_computation','input_sha256':hashlib.sha256(a.input.read_bytes()).hexdigest(),'definition':'cohort: revenue - paid*v - F; pilot: N*delta_paid_rate*(price-v)-K; RUB per first-month cohort','assumptions':data,'cohort_scenarios':cohort,'pilot_scenarios':pilot,'pilot_break_even_additional_paid_rate':str(D(q['allocated_incremental_cost_rub'])/(D(q['eligible'])*margin)) if margin>0 else None}
    with a.output.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({'cohort':cohort,'pilot':pilot,'break_even_rate':result['pilot_break_even_additional_paid_rate']}))
