import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import io

ROOT = Path(__file__).resolve().parents[1]
def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

loc = module('locations', ROOT/'skills/google-maps-scraper/scripts/locations.py')
build = module('build_locations', ROOT/'scripts/build_locations.py')
scrape = module('scrape_locations_test', ROOT/'skills/google-maps-scraper/scripts/scrape.py')


class CatalogTests(unittest.TestCase):
    def test_snapshot_integrity_and_counts(self):
        manifest = json.loads((loc.DATA/'manifest.json').read_text())['countries']
        self.assertEqual(set(manifest), set(build.COUNTRIES))
        for country, info in manifest.items():
            with self.subTest(country=country):
                path = loc.DATA/f'{country}.csv'
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), info['csv_sha256'])
                with path.open(encoding='utf-8', newline='') as handle:
                    rows = list(csv.DictReader(handle))
                self.assertEqual(len(rows), info['locality_rows'])
                self.assertEqual(len({r['postal_code'] for r in rows}), info['postal_codes'])
                identities = set()
                for row in rows:
                    self.assertEqual(row['country'], country)
                    self.assertTrue(row['postal_code'] and row['city'])
                    identity = tuple(row[f] for f in build.FIELDS[:5])
                    self.assertNotIn(identity, identities)
                    identities.add(identity)
                    for field, bound in [('latitude', 90), ('longitude', 180)]:
                        if row[field]:
                            self.assertTrue(-bound <= float(row[field]) <= bound)

    def test_known_postal_city_pairs_and_leading_zeros(self):
        for country, postal, city in [('US','02108','Boston'), ('DE','04109','Leipzig'),
                ('CH','8001','Zürich'), ('FR','75001','Paris'), ('NL','1011','Amsterdam')]:
            with self.subTest(country=country):
                rows = loc.select([country], city=city, prefix=postal, limit=0)
                self.assertTrue(any(r['postal_code'] == postal for r in rows))

    def test_us_state_filter_and_unique_codes(self):
        rows = loc.select(['US'], region='CA', limit=0)
        self.assertGreater(len(rows), 1000)
        self.assertTrue(all(r['region_code'] == 'CA' for r in rows))
        self.assertEqual(len(rows), len({r['postal_code'] for r in rows}))
        self.assertEqual(rows, loc.select(['US'], region='California', limit=0))

    def test_city_accent_filter_and_language_override(self):
        rows = loc.select(['CH'], city='Zurich', limit=2, language='fr')
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r['city']=='Zürich' and r['language']=='fr' for r in rows))

    def test_default_pilot_limit(self):
        self.assertEqual(len(loc.select(['US'])), 25)
        self.assertEqual(loc.select(['US'], city='not a real city'), [])

    def test_generated_csv_integrates_with_scraper(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'pilot.csv'
            with patch('sys.stdout', new=io.StringIO()):
                self.assertEqual(loc.main(['--countries','US','--city','Boston',
                    '--limit','2','--output',str(output)]), 0)
                stream = io.StringIO()
                with patch('sys.stdout', stream):
                    self.assertEqual(scrape.main(['--query','dentist','--locations-file',str(output),
                        '--dry-run']), 0)
                plan = json.loads(stream.getvalue())
                self.assertEqual(len(plan['queries']), 2)
                self.assertTrue(all(q['gl']=='us' and q['hl']=='en' for q in plan['queries']))
                self.assertTrue(all('Boston' in q['q'] for q in plan['queries']))
            with patch('sys.stderr', new=io.StringIO()), self.assertRaises(SystemExit):
                loc.main(['--countries','US','--output',str(output)])

    def test_source_validation_and_german_filter(self):
        text = 'DE\t04109\tLeipzig\tSachsen\t13\t\t\t\t\t51.3\t12.3\t4\n'
        text += 'DE\t99999\tMailbox\tRegion\t13\t\t\t\t\t51\t12\t1\n'
        rows, count = build.normalize(text, 'DE')
        self.assertEqual(count, 2)
        self.assertEqual([r['postal_code'] for r in rows], ['04109'])
        with self.assertRaises(ValueError):
            build.normalize(text, 'US')
        with self.assertRaises(ValueError):
            build.normalize(text.replace('51.3','nan'), 'DE')
        with self.assertRaises(ValueError):
            build.normalize('', 'US')


if __name__ == '__main__':
    unittest.main()
