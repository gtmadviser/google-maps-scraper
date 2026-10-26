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
