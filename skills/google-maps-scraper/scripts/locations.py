#!/usr/bin/env python3
"""Select bundled postal localities into scraper-ready CSV without spending API credits."""
import argparse
import csv
import json
from pathlib import Path
import sys
import unicodedata

DATA = Path(__file__).resolve().parents[1] / 'assets/locations'
LANGUAGES = dict(US='en', DE='de', AT='de', CH='de', FR='fr', ES='es', IT='it', NL='nl',
                 BE='nl', GB='en', PL='pl', PT='pt', DK='da', SE='sv', NO='no', FI='fi', CZ='cs')
FIELDS = ['location', 'country', 'language', 'postal_code', 'city', 'region', 'region_code']


def folded(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value.casefold())
                   if not unicodedata.combining(c))


def select(countries, region='', city='', prefix='', limit=25, language='', data=DATA):
    selected, seen = [], set()
    for country in countries:
        with (data / f'{country}.csv').open(encoding='utf-8', newline='') as handle:
            for row in csv.DictReader(handle):
                if region and folded(region) not in (folded(row['region']), folded(row['region_code'])):
                    continue
                if city and folded(city) != folded(row['city']):
                    continue
                if prefix and not row['postal_code'].casefold().startswith(prefix.casefold()):
                    continue
                identity = (country, row['postal_code'])
                if identity in seen:
                    continue
                seen.add(identity)
                # Region disambiguates same-named cities; no dependence on estimated coordinates.
                location = ' '.join(dict.fromkeys(x for x in
                    (row['postal_code'], row['city'], row['region_code']) if x))
                selected.append({'location': location, 'country': country.lower(),
                    'language': language or LANGUAGES[country],
                    **{k: row[k] for k in FIELDS[3:]}})
                if limit and len(selected) >= limit:
                    return selected
    return selected


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--countries', nargs='+', help='Country codes, e.g. US or DE AT CH')
    parser.add_argument('--list', action='store_true', help='Show available datasets and counts')
    parser.add_argument('--region', default='', help='Exact state/region name or code, e.g. CA or Bayern')
    parser.add_argument('--city', default='', help='Exact city name, case/accent insensitive')
    parser.add_argument('--postal-prefix', default='')
    parser.add_argument('--language', default='', help='Override default result language, e.g. fr for western Switzerland')
    parser.add_argument('--limit', type=int, default=25, help='Pilot size, default 25; 0 selects all matching codes')
    parser.add_argument('--output', default='output/locations.csv')
    args = parser.parse_args(argv)
    manifest = json.loads((DATA / 'manifest.json').read_text())['countries']
    if args.list:
        for country, info in manifest.items():
            print(f"{country}: {info['postal_codes']:,} codes; {info['granularity']}")
        return 0
    if not args.countries or args.limit < 0:
        parser.error('Provide --countries and a nonnegative --limit.')
    countries = list(dict.fromkeys(c.upper() for c in args.countries))
    unknown = set(countries) - manifest.keys()
    if unknown:
        parser.error('Unavailable countries: ' + ', '.join(sorted(unknown)) + '; use --list.')
    rows = select(countries, args.region, args.city, args.postal_prefix, args.limit, args.language)
    if not rows:
        parser.error('No matching locations; check --list and use an exact city/region name or postal prefix.')
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    # A pilot should never accidentally overwrite a location plan already used by a scrape.
    try:
        with target.open('x', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
    except FileExistsError:
        parser.error('Output already exists; choose a new --output or deliberately remove the old file.')
    print(f'{len(rows)} locations -> {target}. At 3 pages/location: up to {len(rows)*3} pages before retries.')
    print('No API calls made. Review the CSV, then use scrape.py --locations-file with --dry-run.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
