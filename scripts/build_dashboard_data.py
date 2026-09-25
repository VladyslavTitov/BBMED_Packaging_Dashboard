#!/usr/bin/env python3
"""Import the supplied final dashboard's data without replacing its newer energy model.

The source HTML is kept unchanged as an auditable snapshot. The older workbook
ETL is preserved separately as build_legacy_dashboard_data.py, and cannot
silently overwrite the current runtime schema.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / 'reference' / 'BBMED_Final_Dynamic_Insight_Dashboard.html'


def read_snapshot(path):
    html = path.read_text(encoding='utf-8')
    script = re.search(r'<script>(.*?)</script>', html, re.S)
    if not script:
        raise ValueError('Expected an inline dashboard data script')
    decoder = json.JSONDecoder()
    operations = decoder.raw_decode(script[1].split('const D=', 1)[1])[0]
    energy = decoder.raw_decode(script[1].split('const EN=', 1)[1])[0]
    return operations, energy


def validate(operations, energy):
    union = operations['union']
    ids = {str(row['order']) for row in union}
    if len(ids) != len(union):
        raise ValueError('Duplicate normalized order keys')
    for table in ['manual_events', 'mes_reason_events']:
        if any(str(row['order']) not in ids for row in operations[table]):
            raise ValueError(f'{table} references an unknown order')
    for row in operations['comparisons']:
        if str(row['order']) not in ids:
            raise ValueError('Reconciliation references an unknown order')
    meter_ids = {m['meter'] for m in energy['meters']}
    for row in energy['orders']:
        if str(row['order']) not in ids:
            raise ValueError('Energy allocation references an unknown order')
        if set(row['meter_kwh']) - meter_ids:
            raise ValueError('Energy allocation references an unknown meter')
    for row in energy['daily_meter']:
        if row['meter'] not in meter_ids:
            raise ValueError('Daily energy references an unknown meter')
    if abs(sum(row['kwh'] for row in energy['orders'])-energy['summary']['allocated_order_kwh'])>0.01:
        raise ValueError('Order allocations and summary do not reconcile')
    for row in energy['orders']:
        if abs(sum(row['meter_kwh'].values())-row['kwh'])>0.01:
            raise ValueError('Per-meter contributions do not reconcile to order energy')
    total = sum(row['kwh'] for row in energy['daily'])
    if abs(total - energy['summary']['total_kwh']) > 0.01:
        raise ValueError('Daily energy and summary do not reconcile')


def build(source=DEFAULT_SOURCE, output=ROOT / 'data' / 'dashboard.json'):
    operations, energy = read_snapshot(source)
    validate(operations, energy)
    payload = {'meta': {'schemaVersion': 3, 'source': source.name,
                       'sourceSha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                       'method': 'Imported supplied final-dashboard snapshot; no raw meter reprocessing',
                       'energyWorkbook': 'source-data/21.update_energy_data.xlsx'},
               'operations': operations, 'energy': energy}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf-8')
    print(f'Built {output.name}: {len(operations["union"])} union orders, '
          f'{len(energy["orders"])} energy-linked orders, '
          f'{energy["summary"]["total_kwh"]:.3f} kWh')
    return payload


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()
    build(args.source)
