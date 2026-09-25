import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_dashboard_data import build, validate

class IntegrationTests(unittest.TestCase):
    def test_snapshot_rebuild_and_relationships(self):
        with tempfile.TemporaryDirectory() as folder:
            payload=build(output=Path(folder)/'dashboard.json')
        runtime=json.loads((ROOT/'data/dashboard.json').read_text())
        self.assertEqual(payload,runtime)
        self.assertEqual(len(payload['operations']['union']),565)
        self.assertEqual(len(payload['energy']['orders']),80)
        self.assertAlmostEqual(payload['energy']['summary']['total_kwh'],8426.28561988478)
        self.assertAlmostEqual(sum(r['kwh'] for r in payload['energy']['daily_meter']),payload['energy']['summary']['total_kwh'],places=5)

    def test_reject_broken_order_relationship(self):
        payload=json.loads((ROOT/'data/dashboard.json').read_text())
        payload['energy']['orders'][0]['order']='missing-order'
        with self.assertRaisesRegex(ValueError,'unknown order'):
            validate(payload['operations'],payload['energy'])

    def test_active_entrypoint_uses_current_assets(self):
        html=(ROOT/'index.html').read_text()
        self.assertIn('Final Insight Dashboard',html)
        for asset in ['styles.css','app.js','public/semantic-model.png','public/data-workflow.png']:
            self.assertIn(asset,html)
            self.assertTrue((ROOT/asset).is_file())
        self.assertNotIn('analytics.js',html)
        self.assertNotIn('const D=',html)

if __name__=='__main__': unittest.main()
