---
name: google-maps-scraper
description: Find Google Maps business listings by category and location through Serper.dev, then export deduplicated CSV and JSON with request caps and resumable pages. Use for local business discovery, directory research, or market mapping; does not find owner emails or launch outreach.
---

# Google Maps Scraper

Use `scripts/scrape.py` relative to this skill folder. Requires Python 3.10+ and the user's `SERPER_API_KEY` (also accepts `SERPER_DEV_KEY`) in the process environment. No dependencies. Never print credentials, place them in commands, or borrow a different project's key.

1. Establish the category, locations, country/language, output folder, and request cap from the request. For multiple locations use repeated `--location` or a CSV with `location,country` and optional `language`. Preserve postal codes as strings.
2. Run `--dry-run` first to inspect the query count and maximum pages. It needs no key and makes no network calls. If the user's scope already authorizes the run and cap, proceed; otherwise get the missing scope/budget before paid requests. Do not expand a small pilot into a nationwide grid without authorization.
3. Execute with the agreed `--max-requests`. The default is 30 attempts per invocation; retries count. Default maximum pages is 3 per query. Use a small pilot to inspect relevance before scaling.
4. Read `report.json`, inspect a sample, and hand off `places.csv` / `places.json` with counts, completion status, and coverage limitations. A nonzero exit or `partial` report means the run is unfinished. Resume with identical arguments/output; a new directory means new paid requests. The cap resets on each invocation, so account for earlier spend before resuming.

```bash
python3 <skill-folder>/scripts/scrape.py --query 'dentist' \
  --location 'Berlin' --country de --language de \
  --max-pages 3 --max-requests 10 --output output/berlin-dentists --dry-run
```

Remove `--dry-run` to execute. Successful pages are cached in SQLite; do not run concurrent processes in the same output directory. Use a new directory only for a deliberately fresh search or changed configuration.

The endpoint is `/places`; do not add paid detail/review enrichment implicitly. Each successful page used one credit in the original workflow; verify current Serper billing before quoting costs. The cap bounds attempts, not dollars or unique businesses. Search results are not exhaustive; neighboring locations overlap, and country/location terms are not strict geographic filters. Full final pages indicate possible truncation. Do not describe results as all businesses in an area.

CIDs remain strings. Do not deduplicate by domain alone: chains have multiple branches. CSV prefixes formula-like strings (including international phone numbers) with an apostrophe; JSON preserves the original values. The export contains businesses, not owner contacts or verified emails. Qualification, relationship exclusions, contact enrichment, and campaign enrollment are separate tasks, outside this skill's authorization.


## Bundled postal locations

For country/state/city coverage, use `scripts/locations.py --list`, then generate a scraper-ready CSV from `assets/locations/`. No network or API key is needed. For example:

```bash
python3 <skill-folder>/scripts/locations.py --countries US --region CA \
  --limit 25 --output output/california.csv
```

Pass the CSV to `scrape.py --locations-file output/california.csv`. City/region matching is exact but ignores case and accents; region also matches source codes. Use `--postal-prefix` for a narrower area, `--language` for multilingual regions, and `--limit 0` only when all matching codes are intended. The default limit is 25 globally, not per country; pilot countries separately. Existing output files are not overwritten.

Read `assets/locations/README.md` before claiming coverage or redistributing data. US plus 16 European countries are bundled with GeoNames attribution and checksums. UK/NL are postcode districts/prefixes. Germany excludes codes without a populated-place match; other sources can include special-use codes. The selector preserves leading zeros and chooses one locality per postal code after filtering; this can omit other settlements sharing the code. A postal list is not proof of complete business coverage. Do not infer residential status, population, or geographic completeness from this catalog.
