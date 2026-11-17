"""Независимая проверка CSV через Fraction; не вызывает analyze_table."""
import argparse
import csv
import hashlib
import json
from fractions import Fraction
from pathlib import Path
from datetime import datetime, timezone


def check(csv_path, result_path):
    rows = list(csv.DictReader(csv_path.open(encoding='utf-8-sig', newline='')))
    result = json.loads(result_path.read_text(encoding='utf-8'))
    checks = []
    for group in result['groups']:
        selected = [r for r in rows if all(r[k] == v for k, v in group['group'].items())]
        for key, observed in group['metrics'].items():
            d = observed['definition']
            needed = d['numerator'] + d.get('denominator', [])
            if any(r[c] in ('', 'NA') for r in selected for c in needed):
                assert observed['value'] is None and observed['status'] == 'missing'
                expected = None
            else:
                numerator = sum(Fraction(r[c]) for r in selected for c in d['numerator'])
                denominator = sum(Fraction(r[c]) for r in selected for c in d['denominator']) if 'denominator' in d else 1
                if denominator == 0:
                    assert observed['value'] is None and observed['status'] == 'zero_denominator'
                    expected = None
                else:
                    expected = numerator / denominator * Fraction(d.get('multiplier', '1'))
                    # Tolerance is half the documented rounding unit, independent of Decimal.
                    assert abs(Fraction(observed['value']) - expected) <= Fraction(1, 2 * 10 ** d['rounding'])
            checks.append({'group': group['group'], 'metric': key, 'exact_fraction': str(expected) if expected is not None else None, 'observed': observed['value'], 'pass': True})
    return {'checked_at': datetime.now(timezone.utc).isoformat(), 'method': 'csv.DictReader + fractions.Fraction; no analyze_table import', 'input_sha256': hashlib.sha256(csv_path.read_bytes()).hexdigest(), 'result_sha256': hashlib.sha256(result_path.read_bytes()).hexdigest(), 'checks': checks}


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--input', type=Path, required=True); p.add_argument('--result', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); report = check(a.input, a.result)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open('x', encoding='utf-8') as f: json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({'passed': len(report['checks']), 'output': str(a.output)}))
