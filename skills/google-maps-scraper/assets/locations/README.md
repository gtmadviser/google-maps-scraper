# Bundled postal locations

Snapshot retrieved October 26, 2026 from [GeoNames postal downloads](https://download.geonames.org/export/zip/).

**Data license: [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/), attributed to [GeoNames](https://www.geonames.org/).** This data is separate from the repository's MIT code license. Retain attribution and identify changes when redistributing it. See the [source README](https://download.geonames.org/export/zip/readme.txt).

Changes: converted country archives to UTF-8 CSV, selected fields, sorted records, removed duplicate locality rows (retaining the first source coordinate pair), and filtered German codes to those with at least one GeoNames accuracy 4 or 6 match, following the original DACH locality approach. Other countries retain the source's postal codes, including possible special-use codes. This is a locality search aid, not postal address validation.

| Country | Code | Distinct codes | Locality rows | Granularity |
|---|---|---:|---:|---|
| Austria | AT | 2,501 | 19,002 | postal code |
| Belgium | BE | 1,146 | 2,781 | postal code |
| Switzerland | CH | 3,362 | 4,466 | postal code |
| Czechia | CZ | 2,694 | 15,507 | postal code |
| Germany | DE | 8,159 | 16,337 | postal code |
| Denmark | DK | 1,159 | 1,159 | postal code |
| Spain | ES | 11,150 | 37,867 | postal code |
| Finland | FI | 3,576 | 3,576 | postal code |
| France | FR | 20,418 | 51,586 | postal code |
| United Kingdom | GB | 3,002 | 27,450 | postal prefix/district |
| Italy | IT | 4,736 | 18,415 | postal code |
| Netherlands | NL | 4,086 | 4,321 | postal prefix/district |
| Norway | NO | 5,132 | 5,132 | postal code |
| Poland | PL | 20,299 | 72,898 | postal code |
| Portugal | PT | 197,772 | 206,942 | postal code |
| Sweden | SE | 18,887 | 18,887 | postal code |
| United States | US | 41,488 | 41,490 | postal code |

## Coverage and use

- There can be multiple localities for one postal code. The selector filters localities first, then picks the first matching locality per country/code to avoid buying duplicate postal-code searches. This can miss other settlements sharing that code; add explicit city searches when needed.
- UK data contains outward postcode districts (e.g. SW1A), not full delivery postcodes. Netherlands data contains four-digit prefixes, not full six-character postcodes. Those are useful search areas but are broader than individual postal addresses.
- Germany's filter is a heuristic for populated localities, not a guarantee that every retained code is residential or current. Other files may include company/postbox codes. Austria/Switzerland use the unfiltered GeoNames snapshots, not the earlier project's custom curated counts.
- US data is the GeoNames US archive; territories with their own archives are not bundled separately. There is no ZIP type or population filter. Codes and administrative fields can be missing, dated or imperfect; no complete/current registry claim is made.
- Coordinates are source estimates. The scraper uses textual locations, not these coordinates, and does not enforce geographic boundaries.
- Language defaults are conveniences, not inferred per locality. Use `--language fr` for French-speaking Switzerland/Belgium, for example, and use a category in the appropriate local language.
- `--city` and `--region` match exact source names (case/accent insensitive); region also accepts its source code. For Vienna use `--region Wien`, because city names can include districts. No fuzzy geocoding is performed.
- The default 25-code pilot is sorted, not a representative geographic sample. A multi-country limit is global and fills countries in argument order; run a separate pilot per country to test each market.

## Verification and refresh

`manifest.json` records source URLs, archive checksums, CSV checksums, retrieval date, source Last-Modified headers, counts, and transformations. Last-Modified is an archive timestamp, not a guarantee that every postal record was recently updated. An additional archive-to-CSV check verified every exported locality and coordinate pair against the original downloads, with no eligible locality lost. Offline tests validate every CSV's checksum, country, unique locality keys, counts and coordinate bounds, plus known postal/city examples and scraper integration.

To refresh from the repository root (network downloads only; no Serper key or credits):

```bash
python3 scripts/build_locations.py --as-of YYYY-MM-DD
python3 -m unittest discover -s tests -v
```

Replace the date with the actual retrieval date. Inspect changes before committing a refreshed snapshot. Keep all 17 CSVs together with this attribution and manifest when copying the skill.

## US comparison with Eric's repository

Checked against [Eric's US CSV](https://github.com/elnumae/ericscoldoutboundskills/blob/main/Common%20Outbound%20Lists/us-zip-codes.csv), Git blob `ce1155485382df13b2e14d83bdfb19b71c5b6da7`, on October 26, 2026. The local file's Git blob hash matched GitHub's current file metadata.

| Check | Result |
|---|---:|
| Eric CSV rows / unique ZIPs after zero-padding | 42,735 |
| Eric ZIPs requiring leading-zero restoration | 3,761 |
| Bundled GeoNames unique US ZIPs | 41,488 |
| ZIPs shared by both | 41,340 |
| Only in Eric's CSV | 1,395 |
| Only in GeoNames | 148 |

The mismatch does not establish which individual codes are valid: releases, territories and special-use coverage can differ. Eric's skill text says 42,734 entries; the actual checked CSV has 42,735. We publish GeoNames rather than merging two differently scoped lists, because its source and dataset license are explicit. No rows from Eric's CSV were copied. This comparison is a recorded one-time check, not a dependency of the offline test suite.
