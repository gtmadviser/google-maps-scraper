import importlib.util
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import urllib.error

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/google-maps-scraper/scripts/scrape.py'
spec = importlib.util.spec_from_file_location('scrape', SCRIPT)
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)


class FakeClient:
    def __init__(self, batches):
        self.batches = iter(batches)
        self.attempts = 0

    def fetch(self, body):
        self.attempts += 1
        result = next(self.batches)
        if isinstance(result, Exception):
            raise result
        return result


class Tests(unittest.TestCase):
    def args(self, output, **overrides):
        data = dict(query='dentist', location=['Berlin'], locations_file=None, country='de',
                    language='de', max_pages=3, max_requests=30, output=output)
        return SimpleNamespace(**(data | overrides))

    def test_partial_resume_and_dedupe(self):
        full = [{'cid': str(i), 'title': 'Clinic'} for i in range(10)]
        with tempfile.TemporaryDirectory() as output:
            args = self.args(output)
            with self.assertRaises(s.ScrapeError):
                s.run(args, FakeClient([full, s.BudgetReached('cap')]))
            self.assertEqual(json.loads((Path(output)/'report.json').read_text())['status'], 'partial')
            client = FakeClient([[full[0], {'cid': '999', 'title': 'New'}]])
            report = s.run(args, client)
            self.assertEqual(report['unique_places'], 11)
            self.assertEqual(report['cached_pages'], 1)
            self.assertEqual(client.attempts, 1)
            again = s.run(args, FakeClient([]))
            self.assertEqual(again['request_attempts_this_run'], 0)
            self.assertEqual(again['unique_places'], 11)

    def test_different_run_rejected(self):
        with tempfile.TemporaryDirectory() as output:
            s.run(self.args(output), FakeClient([[]]))
            with self.assertRaises(s.ScrapeError):
                s.run(self.args(output, query='hotel'), FakeClient([]))

    def test_retry_counts_toward_cap(self):
        error = urllib.error.HTTPError(s.ENDPOINT, 429, 'limited', {}, None)
        client = s.Client('fake-key', 1, delay=0)
        with patch.object(s.urllib.request, 'urlopen', side_effect=error) as request, patch.object(s.time, 'sleep'):
            with self.assertRaises(s.BudgetReached):
                client.fetch({'q': 'dentist'})
            self.assertEqual(request.call_count, 1)
            self.assertEqual(client.attempts, 1)

    def test_auth_not_retried(self):
        error = urllib.error.HTTPError(s.ENDPOINT, 401, 'bad key', {}, None)
        with patch.object(s.urllib.request, 'urlopen', side_effect=error) as request:
            with self.assertRaises(s.ScrapeError):
                s.Client('fake-key', 30).fetch({})
            self.assertEqual(request.call_count, 1)

    def test_long_cid_preserved(self):
        raw = b'{"places":[{"cid":18446744073709551615,"title":"Demo"}]}'
        with patch.object(s.urllib.request, 'urlopen', return_value=io.BytesIO(raw)):
            result = s.Client('fake-key', 1).fetch({})
        self.assertEqual(result[0]['cid'], '18446744073709551615')

    def test_bad_schema_not_empty_success(self):
        with patch.object(s.urllib.request, 'urlopen', return_value=io.BytesIO(b'{"error":"bad"}')):
            with self.assertRaises(s.ScrapeError):
                s.Client('fake-key', 1).fetch({})

    def test_no_id_does_not_collapse_branches(self):
        a = {'title': 'Chain', 'address': 'Street 1', 'website': 'https://example.com'}
        b = dict(a, address='Street 2')
        self.assertNotEqual(s.place_key(a, {}), s.place_key(b, {}))
        self.assertNotEqual(s.place_key({'title': 'A'}, {}), s.place_key({'title': 'B'}, {}))

    def test_csv_safety(self):
        self.assertEqual(s.csv_safe('+49 123'), "'+49 123")
        self.assertEqual(s.csv_safe('  =HYPERLINK("x")'), "'  =HYPERLINK(\"x\")")

    def test_locations_preserve_postal_zero(self):
        with tempfile.TemporaryDirectory() as output:
            p = Path(output)/'locations.csv'
            p.write_text('location,country,language\n04109,de,de\n04109,de,de\n')
            result = s.queries(self.args(output, location=[], locations_file=p))
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['q'], 'dentist in 04109')

    def test_dry_run_without_key_or_files(self):
        with tempfile.TemporaryDirectory() as output, patch.dict(s.os.environ, {}, clear=True):
            target = Path(output)/'unused'
            with patch('sys.stdout', new=io.StringIO()):
                self.assertEqual(s.main(['--query', 'dentist', '--location', 'Berlin', '--dry-run', '--output', str(target)]), 0)
            self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
