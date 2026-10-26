#!/usr/bin/env python3
"""Download and normalize attributed GeoNames postal locality snapshots (no Serper calls)."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import urllib.request
import zipfile

COUNTRIES = 'US DE AT CH FR ES IT NL BE GB PL PT DK SE NO FI CZ'.split()
ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'skills/google-maps-scraper/assets/locations'
FIELDS = ['country', 'postal_code', 'city', 'region', 'region_code', 'latitude', 'longitude']


def normalize(text, country):
    # Match the locality filter used in the original DACH workflow. Keep all
    # aliases of eligible codes, but exclude DE codes without a populated-place match.
    eligible = {p[1] for line in text.splitlines() if len(p := line.split('\t')) >= 12
                and p[11] in ('4', '6')} if country == 'DE' else None
    records = {}
    source_rows = 0
    for line in text.splitlines():
        if not line.strip():
            continue
        source_rows += 1
        parts = line.split('\t')
        if len(parts) < 11 or parts[0] != country or not parts[1].strip() or not parts[2].strip():
            raise ValueError(f'{country}: malformed source row {source_rows}')
        for value, bound in ((parts[9], 90), (parts[10], 180)):
            if value and (not math.isfinite(float(value)) or abs(float(value)) > bound):
                raise ValueError(f'{country}: invalid coordinate on row {source_rows}')
        if eligible is not None and parts[1] not in eligible:
            continue
        row = dict(zip(FIELDS, [country, parts[1].strip(), parts[2].strip(), parts[3].strip(),
                               parts[4].strip(), parts[9], parts[10]]))
        # Preserve distinct locality names: filter by city BEFORE reducing to one query per code.
        identity = tuple(row[k] for k in FIELDS[:5])
        records.setdefault(identity, row)
    if not records:
        raise ValueError(f'{country}: empty source')
    return sorted(records.values(), key=lambda r: tuple(r[k] for k in FIELDS[:5])), source_rows


def build(country, cache, as_of):
    url = f'https://download.geonames.org/export/zip/{country}.zip'
    archive = cache / f'{country}.zip'
    # Downloads are explicit on every rebuild; the cache records the exact source used.
    with urllib.request.urlopen(url, timeout=90) as response:
        blob = response.read()
        modified = response.headers.get('Last-Modified')
    archive.write_bytes(blob)
    with zipfile.ZipFile(io.BytesIO(blob)) as zipped:
        rows, raw_count = normalize(zipped.read(f'{country}.txt').decode('utf-8'), country)
    output = DEST / f'{country}.csv'
    with output.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    return country, {'source_url': url, 'retrieved_on': as_of, 'source_last_modified': modified,
        'source_sha256': hashlib.sha256(blob).hexdigest(),
        'csv_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        'source_rows': raw_count, 'locality_rows': len(rows),
        'postal_codes': len({r['postal_code'] for r in rows}),
        'filter': 'DE: keep postal codes with at least one accuracy 4 or 6 source row' if country == 'DE' else 'none; may include special-use postal codes',
        'missing_coordinates': sum(not r['latitude'] or not r['longitude'] for r in rows),
        'granularity': 'postal prefix/district' if country in ('GB', 'NL') else 'postal code'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of', required=True, help='Retrieval date YYYY-MM-DD')
    args = parser.parse_args()
    from datetime import date
    date.fromisoformat(args.as_of)
    cache = ROOT / '.cache/geonames'
    cache.mkdir(parents=True, exist_ok=True)
    DEST.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        result = dict(pool.map(lambda code: build(code, cache, args.as_of), COUNTRIES))
    manifest = {'source': 'GeoNames', 'license': 'CC-BY-4.0',
                'license_url': 'https://creativecommons.org/licenses/by/4.0/',
                'source_readme': 'https://download.geonames.org/export/zip/readme.txt',
                'countries': dict(sorted(result.items()))}
    (DEST / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    for country, info in sorted(result.items()):
        print(country, info['postal_codes'], 'codes;', info['locality_rows'], 'locality rows')


if __name__ == '__main__':
    main()
