"""One isolated, reproducible evaluation. No network and no changes to canonical projects."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter, defaultdict
from fractions import Fraction
import argparse
import csv
import hashlib
import io
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.import_materials import register
from scripts.analyze_table import run

EXPECTED = ['Administrative', 'Administrative_Duration', 'Informational', 'Informational_Duration',
            'ProductRelated', 'ProductRelated_Duration', 'BounceRates', 'ExitRates', 'PageValues',
            'SpecialDay', 'Month', 'OperatingSystems', 'Browser', 'Region', 'TrafficType',
            'VisitorType', 'Weekend', 'Revenue']
SOURCE = 'https://archive.ics.uci.edu/dataset/468/online+shoppers+purchasing+intention+dataset'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def write(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--project', type=Path, required=True)
    args = parser.parse_args()
    source, project = args.input.resolve(), args.project.resolve()
    assert source.is_file() and source.is_relative_to(ROOT)
    assert project.is_relative_to(ROOT) and not project.exists()
    started = datetime.now(timezone.utc)
    with source.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f, strict=True)
        assert reader.fieldnames == EXPECTED
        rows = list(reader)
    assert len(rows) == 12330
    assert all(set(row) == set(EXPECTED) and all(v is not None and v != '' for v in row.values()) for row in rows)
    assert Counter(r['Revenue'] for r in rows) == {'TRUE':1908, 'FALSE':10422}
    assert set(r['Weekend'] for r in rows) == {'TRUE','FALSE'}
    (project/'inputs').mkdir(parents=True)
    raw = project/'inputs/online_shoppers_intention.csv'
    shutil.copyfile(source, raw)
    assert sha(raw) == sha(source)
    attributed = {'title':'Online Shoppers Purchasing Intention Dataset', 'creators':['C. Sakar','Yomi Kastro'],
       'year':2018, 'doi':'https://doi.org/10.24432/C5F88Q', 'source_url':SOURCE,
       'license':'CC BY 4.0', 'license_url':'https://creativecommons.org/licenses/by/4.0/',
       'owner_original_path':source.relative_to(ROOT).as_posix(), 'owner_original_absolute_path':str(source),
       'original_sha256':sha(raw), 'local_copy':'inputs/online_shoppers_intention.csv',
       'downloaded_by':'owner before this task', 'redownloaded':False,
       'official_description_accessed_at':started.isoformat(),
       'comparison_scope':'18 columns = 17 features + Revenue; 12330 rows, 1908 TRUE, 10422 FALSE; no empty cells. UCI does not publish a file hash here; identity verified locally, not against an official checksum.',
       'modification':'Original bytes unchanged. Derived CSV retains all 18 cells per row and adds three explicitly defined fields.'}
    write(project/'inputs/attribution-v1.json', attributed)
    original = register(project,'S001',raw,'csv',origin=SOURCE, synthetic=False,
        limitations=['Исторические наблюдательные данные; год сессий не указан в CSV. Это не пользователи RelayBox или МегаФона.',
                    'Revenue — признак покупки, не денежная выручка. Строки не являются повторными визитами одного пользователя.'])
    derived = project/'inputs/session-counts-v1.csv'
    with derived.open('x',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=EXPECTED+['SessionCount','PurchaseCount','ObservationPeriod'],lineterminator='\n')
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row,SessionCount='1',PurchaseCount='1' if row['Revenue']=='TRUE' else '0',
                                 ObservationPeriod='UCI_468_sample_year_unspecified'))
    with derived.open(encoding='utf-8',newline='') as f:
        normalized=list(csv.DictReader(f))
    assert len(normalized)==len(rows)
    assert all({k:n[k] for k in EXPECTED}==r for n,r in zip(normalized,rows))
    write(project/'inputs/derivation-v1.json', {
       'input_sha256':sha(raw),'output_sha256':sha(derived),'rows_in':len(rows),'rows_out':len(normalized),
       'all_original_cells_equal':True,'order_preserved':True,'deduplication':False,'imputation':False,
       'locator_mapping':'Derived CSV physical row n equals original physical row n; data rows 2..12331.',
       'definitions':{'SessionCount':'1 per source row','PurchaseCount':'TRUE -> 1; FALSE -> 0; other values rejected',
                      'ObservationPeriod':'entire historical sample; actual year unknown; Month retained'},
       'purpose':'Importer already accepts the original. Additive lossless derivation supplies numeric indicators for the existing sum/ratio calculator.'})
    register(project,'S002',derived,'csv',origin='Derived from S001/v1; inputs/derivation-v1.json',synthetic=False,
             limitations=['Производный источник; не независимое подтверждение S001. Все исходные ячейки и строки сохранены.'])
    columns={key:{'type':'text','unit':'source literal'} for key in EXPECTED}
    columns.update(SessionCount={'type':'integer','unit':'session','min':0},
                   PurchaseCount={'type':'integer','unit':'session','min':0},
                   ObservationPeriod={'type':'text','unit':'observation window'})
    spec={'columns':columns,'group_by':['ObservationPeriod','Month','VisitorType'],
          'period_column':'ObservationPeriod','missing_values':[''],'synthetic':False,
          'metrics':[{'id':'sessions','operation':'sum','numerator':['SessionCount'],'unit':'session','rounding':0},
                     {'id':'purchases','operation':'sum','numerator':['PurchaseCount'],'unit':'session','rounding':0},
                     {'id':'purchase_rate','operation':'ratio','numerator':['PurchaseCount'],'denominator':['SessionCount'],
                      'multiplier':100,'unit':'%','rounding':4}],
          'constraints':[{'operation':'lte','left':'PurchaseCount','right':'SessionCount'}]}
    write(project/'inputs/metrics-v1.json',spec)
    result=run(project,derived,'inputs/metrics-v1.json','evidence/calculations/by-month-visitor-v1.json',source_id='S002',source_version=1)['result']
    # Independent recount: original CSV only, no derived indicators or calculator output.
    counts=defaultdict(lambda:[0,0])
    visitors=defaultdict(lambda:[0,0])
    for row in rows:
        for bucket in (counts[(row['Month'],row['VisitorType'])],visitors[row['VisitorType']]):
            bucket[0]+=1
            bucket[1]+=int(row['Revenue']=='TRUE')
    for group in result['groups']:
        n,k=counts[(group['group']['Month'],group['group']['VisitorType'])]
        assert group['metrics']['sessions']['value']==str(n)
        assert group['metrics']['purchases']['value']==str(k)
        assert abs(Fraction(group['metrics']['purchase_rate']['value'])-Fraction(100*k,n)) <= Fraction(1,20000)
    def summary(n,k):
        return {'sessions':n,'purchases':k,'non_purchases':n-k,'fraction':str(Fraction(k,n)),'percent':round(100*k/n,4)}
    report={'at':datetime.now(timezone.utc).isoformat(),'input_sha256':sha(raw),'rows':len(rows),
            'revenue':dict(Counter(r['Revenue'] for r in rows)),'overall':summary(len(rows),1908),
            'by_visitor':{key:summary(*value) for key,value in sorted(visitors.items())},
            'by_month_visitor':{month+'|'+visitor:summary(*value) for (month,visitor),value in sorted(counts.items())},
            'groups_checked':len(counts),'all_calculator_groups_match':True,
            'identical_feature_rows_retained':len(rows)-len(set(tuple(row[k] for k in EXPECTED) for row in rows)),
            'original_import_rows':12330,'lossless_derived_rows':12330,'synthetic':False,
            'elapsed_seconds':(datetime.now(timezone.utc)-started).total_seconds()}
    write(project/'evidence/calculations/independent-v1.json',report)
    write(project/'evidence/import-observation-v1.json',{'original_import':original,'runtime_sha256':{p.name:sha(p) for p in (ROOT/'scripts').glob('*.py')}})
    print(json.dumps({key:value for key,value in report.items() if key!='by_month_visitor'},ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
