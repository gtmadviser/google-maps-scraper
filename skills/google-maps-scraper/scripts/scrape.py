#!/usr/bin/env python3
"""Google Maps business listings through Serper. Python 3.10+, no dependencies."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

ENDPOINT = 'https://google.serper.dev/places'
FIELDS = ['cid', 'name', 'category', 'address', 'phone', 'website', 'company_domain',
          'rating', 'reviews_count', 'latitude', 'longitude', 'google_maps_url', 'sources']


class ScrapeError(Exception):
    pass


class BudgetReached(ScrapeError):
    pass


class Client:
    def __init__(self, key, max_requests, retries=2, delay=0.5):
        self.key = key
        self.max_requests = max_requests
        self.retries = retries
        self.delay = delay
        self.attempts = 0

    def fetch(self, body):
        for attempt in range(self.retries + 1):
            if self.attempts >= self.max_requests:
                raise BudgetReached('Request cap reached. Resume with the same output directory.')
            if self.attempts:
                time.sleep(self.delay)
            self.attempts += 1  # Include retries and ambiguous network failures in the cap.
            request = urllib.request.Request(
                ENDPOINT, data=json.dumps(body).encode(), method='POST',
                headers={'X-API-KEY': self.key, 'Content-Type': 'application/json'})
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    data = json.load(response)  # Python integers preserve all CID digits.
                if not isinstance(data, dict) or not isinstance(data.get('places'), list):
                    raise ScrapeError('Unexpected Serper response: expected a places array.')
                if any(not isinstance(p, dict) for p in data['places']):
                    raise ScrapeError('Unexpected place record.')
                for place in data['places']:
                    if place.get('cid') is not None:
                        place['cid'] = str(place['cid'])
                return data['places']
            except urllib.error.HTTPError as error:
                if error.code not in (429, 500, 502, 503, 504) or attempt == self.retries:
                    raise ScrapeError(f'Serper HTTP {error.code}; check your key, balance and plan.') from None
                retry_after = error.headers.get('Retry-After', '')
                wait = float(retry_after) if retry_after.isdigit() else 2 ** attempt
                time.sleep(min(wait, 60))
            except (urllib.error.URLError, TimeoutError):
                if attempt == self.retries:
                    raise ScrapeError('Serper network failure; saved pages can be resumed.') from None
                time.sleep(2 ** attempt)
            except (ValueError, UnicodeError):
                raise ScrapeError('Invalid JSON from Serper; page was not cached.') from None
        raise ScrapeError('Retries exhausted.')


def queries(args):
    result = []
    for location in args.location or []:
        if location.strip():
            result.append({'q': f'{args.query.strip()} in {location.strip()}',
                           'gl': args.country.lower(), 'hl': args.language})
    if args.locations_file:
        with open(args.locations_file, encoding='utf-8-sig', newline='') as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or not {'location', 'country'} <= set(reader.fieldnames):
                raise ScrapeError('Locations CSV needs location,country columns; language is optional.')
            for line, row in enumerate(reader, 2):
                location, country = (row.get('location') or '').strip(), (row.get('country') or '').strip()
                if not location or len(country) != 2 or not country.isalpha():
                    raise ScrapeError(f'Invalid location or two-letter country on CSV row {line}.')
                result.append({'q': f'{args.query.strip()} in {location}', 'gl': country.lower(),
                               'hl': (row.get('language') or args.language).strip()})
    unique = {json.dumps(q, sort_keys=True): q for q in result}
    if not unique:
        raise ScrapeError('Provide --location or --locations-file.')
    return list(unique.values())


def place_key(place, source):
    if place.get('cid'):
        return 'cid:' + str(place['cid'])
    if place.get('placeId'):
        return 'place:' + str(place['placeId'])
    # Avoid merging branches by website alone, or collapsing all missing IDs.
    if place.get('title') and place.get('address'):
        return 'address:' + json.dumps([place['title'].casefold(), place['address'].casefold()])
    return 'record:' + hashlib.sha256(json.dumps([place, source], sort_keys=True).encode()).hexdigest()


def normalize(place, source):
    website = str(place.get('website') or '')
    try:
        domain = urlsplit(website if '://' in website else 'https://' + website).hostname or ''
    except ValueError:
        domain = ''
    cid = str(place.get('cid') or '')
    return dict(zip(FIELDS, [cid, place.get('title', ''), place.get('category', place.get('type', '')),
        place.get('address', ''), place.get('phoneNumber', ''), website, domain.removeprefix('www.'),
        place.get('rating', ''), place.get('ratingCount', ''), place.get('latitude', ''),
        place.get('longitude', ''), f'https://www.google.com/maps?cid={cid}' if cid else '', [source]]))


def csv_safe(value):
    text = str(value) if value is not None else ''
    # Phone numbers and provider text must not become spreadsheet formulas.
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')) else text


def write_json(path, data):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)


def run(args, client):
    plan = queries(args)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    config = {'queries': plan, 'max_pages': args.max_pages, 'endpoint': ENDPOINT}
    config_path = out / 'config.json'
    if config_path.exists() and json.loads(config_path.read_text()) != config:
        raise ScrapeError('Output directory belongs to a different search. Choose a new --output.')
    write_json(config_path, config)
    records, raw_count, pages, cached, capped = {}, 0, 0, 0, 0
    status, failure = 'complete', None
    with sqlite3.connect(out / 'cache.sqlite3') as db:
        db.execute('CREATE TABLE IF NOT EXISTS pages (request TEXT PRIMARY KEY, response TEXT NOT NULL)')
        try:
            for query in plan:
                for page in range(1, args.max_pages + 1):
                    body = {**query, 'page': page}
                    token = json.dumps(body, sort_keys=True)
                    saved = db.execute('SELECT response FROM pages WHERE request=?', (token,)).fetchone()
                    if saved:
                        batch = json.loads(saved[0])
                        cached += 1
                    else:
                        batch = client.fetch(body)
                        with db:
                            db.execute('INSERT INTO pages VALUES (?, ?)', (token, json.dumps(batch)))
                    pages += 1
                    raw_count += len(batch)
                    for place in batch:
                        identity = place_key(place, body)
                        if identity not in records:
                            records[identity] = normalize(place, body)
                        elif body not in records[identity]['sources']:
                            records[identity]['sources'].append(body)
                    if len(batch) < 10:
                        break
                    if page == args.max_pages:
                        capped += 1
        except (ScrapeError, KeyboardInterrupt, sqlite3.Error, ValueError, OSError) as error:
            status = 'partial'
            failure = error
        finally:
            rows = list(records.values())
            write_json(out / 'places.json', rows)
            temp = out / 'places.csv.tmp'
            with temp.open('w', encoding='utf-8-sig', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=FIELDS)
                writer.writeheader()
                for row in rows:
                    writer.writerow({k: csv_safe(json.dumps(v, ensure_ascii=False) if isinstance(v, list) else v)
                                     for k, v in row.items()})
            temp.replace(out / 'places.csv')
            report = {'status': status, 'queries': len(plan), 'pages': pages, 'cached_pages': cached,
                      'request_attempts_this_run': client.attempts, 'max_requests_this_run': args.max_requests,
                      'raw_results': raw_count, 'unique_places': len(rows), 'duplicates': raw_count - len(rows),
                      'queries_at_page_cap': capped}
            write_json(out / 'report.json', report)
    if failure is not None:
        raise ScrapeError(str(failure) or 'Interrupted; resume with the same output directory.')
    return report


def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError('must be at least 1')
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--query', required=True, help='Business category, e.g. dentist')
    parser.add_argument('--location', action='append', help='City/postal code; repeat for multiple locations')
    parser.add_argument('--locations-file', help='CSV with location,country and optional language columns')
    parser.add_argument('--country', default='us', help='Two-letter country code for --location')
    parser.add_argument('--language', default='en')
    parser.add_argument('--max-pages', type=positive, default=3)
    parser.add_argument('--max-requests', type=positive, default=30, help='Per invocation cap, INCLUDING retries')
    parser.add_argument('--output', default='output/maps')
    parser.add_argument('--dry-run', action='store_true', help='Show plan without a key, files or API calls')
    args = parser.parse_args(argv)
    try:
        if not args.query.strip() or len(args.country) != 2 or not args.country.isalpha() or not args.language.strip():
            raise ScrapeError('Use a nonempty query/language and a two-letter country code.')
        plan = queries(args)
        if args.dry_run:
            print(json.dumps({'queries': plan, 'max_pages': args.max_pages,
                'maximum_pages': len(plan) * args.max_pages, 'request_cap': args.max_requests}, indent=2))
            return 0
        key = os.environ.get('SERPER_API_KEY') or os.environ.get('SERPER_DEV_KEY')
        if not key or not key.strip():
            raise ScrapeError('Set SERPER_API_KEY (or SERPER_DEV_KEY) in your environment.')
        report = run(args, Client(key.strip(), args.max_requests))
        print(json.dumps(report, indent=2))
        return 0
    except (ScrapeError, OSError, ValueError, sqlite3.Error) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
