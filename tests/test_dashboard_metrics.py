import json
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from dashboard_metrics import normalize_order, meter_intervals, allocate_energy


class MeterTests(unittest.TestCase):
    def samples(self, values):
        return [(datetime(2026, 1, 1) + timedelta(hours=i), v) for i, v in enumerate(values)]

    def test_consecutive_consumption_not_cumulative_sum(self):
        intervals, issues = meter_intervals(self.samples([785.38, 787.38, 790.38]))
        self.assertEqual(sum(r['delta'] for r in intervals), 5)
        self.assertEqual(issues, 0)

    def test_reset_invalid_and_duplicate_samples(self):
        readings = self.samples([100, 102, 1, 4, None, 12, 13])
        readings.append(readings[1])
        intervals, issues = meter_intervals(readings)
        self.assertEqual(sum(r['delta'] for r in intervals), 6)
        self.assertEqual(issues, 2)
        readings.append((readings[0][0], 99))
        intervals, issues = meter_intervals(readings)
        self.assertEqual(sum(r['delta'] for r in intervals), 4)
        self.assertEqual(issues, 3)

    def test_order_normalization(self):
        self.assertEqual(normalize_order(' 00701234.0 '), '701234')
        self.assertEqual(normalize_order(' ab-12 '), 'AB-12')
        self.assertEqual(normalize_order(''), '')

    def test_allocation_conserves_energy_and_excludes_ambiguous_overlap(self):
        intervals, _ = meter_intervals(self.samples([0, 12]))
        start = datetime(2026, 1, 1)
        periods = [(start, start+timedelta(minutes=30), 'A'),
                   (start+timedelta(minutes=20), start+timedelta(minutes=40), 'B')]
        allocated, unknown = allocate_energy(intervals, periods)
        self.assertAlmostEqual(allocated['A'], 4)
        self.assertAlmostEqual(allocated['B'], 2)
        self.assertAlmostEqual(unknown, 6)
        self.assertAlmostEqual(sum(allocated.values())+unknown, 12)

    def test_supplied_data_reconciliation_and_energy_conservation(self):
        data = json.loads((ROOT/'reference/legacy-dashboard.json').read_text())
        self.assertEqual(len(data['orders']), 430)
        self.assertEqual(sum(r['excelQty'] is not None for r in data['orders']), 263)
        self.assertEqual(len(data['excelOnly']), 135)
        self.assertAlmostEqual(sum(r['delta'] for r in data['energy']['intervals']), 11.22696, places=5)
        self.assertAlmostEqual(sum(r['delta'] for r in data['energy']['orderAllocation'])+data['energy']['unallocatedDelta'], data['energy']['totalDelta'], places=5)
        self.assertEqual(sum(r['produced'] for r in data['periods']), sum(r['produced'] for r in data['orders']))
        self.assertTrue(all(r['excelDurationMin'] is None or r['excelDurationMin'] >= 0 for r in data['orders']))


if __name__ == '__main__':
    unittest.main()
