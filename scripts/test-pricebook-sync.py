import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('sync', Path(__file__).with_name('prepare-pricebook-sync.py'))
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class SyncTests(unittest.TestCase):
    def test_inventory_never_publishes_contacts_or_source_identifiers(self):
        raw = {'rows': [{'last_seen_at': '2026-10-02', 'rooms': 4, 'mamad': None,
                        'phone': 'private', 'description': 'private', 'external_id': 'source-id'}]}
        out = sync.inventory(raw, 'יבנה')
        self.assertIsNone(out['rows'][0]['mamad'])
        self.assertNotIn('phone', out['rows'][0])
        self.assertNotIn('description', out['rows'][0])
        self.assertNotIn('external_id', out['rows'][0])

    def test_missing_batch_file_does_not_touch_published_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'site/data/yavne/pricebook.json'
            target.parent.mkdir(parents=True)
            target.write_text('existing verified data')
            with self.assertRaises(FileNotFoundError):
                sync.prepare(root / 'missing', root / 'site', 'source-sha')
            self.assertEqual(target.read_text(), 'existing verified data')

    def test_quarter_excludes_neighboring_city_partial_ownership_and_duplicates(self):
        row = dict(settlement='יבנה', deal_date='21/07/2026', gush='1', chelka='2', sub_chelka='3',
                   deal_nature='דירה בבית קומות', portion='1', asset_area='100', room_num='4', deal_amount='2000000')
        raw = {'period_from': '2026-07-01', 'period_to': '2026-09-30',
               'rows': [row, row.copy(), {**row, 'settlement': 'גן יבנה'},
                        {**row, 'portion': '.5', 'sub_chelka': '4'}]}
        out = sync.quarter(raw, 'יבנה', {})
        self.assertEqual(out['register_unique_count'], 2)
        self.assertEqual(out['standard_apartment_count'], 1)
        self.assertEqual(out['rows'][0]['_event_date_iso'], '2026-07-21')
        self.assertFalse(out['representative_quarter'])


if __name__ == '__main__':
    unittest.main()
