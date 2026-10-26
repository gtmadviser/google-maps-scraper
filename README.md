# Google Maps Scraper · Serper

**Turn a business category and a list of locations into a deduplicated CSV.**
Bring your own [Serper.dev](https://serper.dev/) key. Python 3.10+, no packages to install, no browser automation, no hosted backend.

Use it for local business research, directories, market mapping, or as the starting point for account research. Run it yourself or give the included skill to your coding agent.

## Get started

1. Create a [Serper account](https://serper.dev/) and get your API key.
2. Clone this repo:

```bash
git clone https://github.com/gtmadviser/google-maps-scraper.git
cd google-maps-scraper
```

3. Set `SERPER_API_KEY` in your environment. On macOS/Linux, this hidden prompt keeps it out of shell history:

```bash
read -r -s -p 'Serper API key: ' SERPER_API_KEY; echo  # bash
export SERPER_API_KEY
```

For zsh, use `read -r -s 'SERPER_API_KEY?Serper API key: '; echo`, then the same `export`. PowerShell: `$env:SERPER_API_KEY = Read-Host -MaskInput 'Serper API key'` (PowerShell 7.1+). `SERPER_DEV_KEY` is also supported. `.env` files are not loaded automatically. Never commit a real key.

4. Preview, then run:

```bash
python3 skills/google-maps-scraper/scripts/scrape.py \
  --query 'dentist' --location 'Berlin' --country de --language de --dry-run

python3 skills/google-maps-scraper/scripts/scrape.py \
  --query 'dentist' --location 'Berlin' --country de --language de \
  --max-pages 3 --max-requests 10 --output output/berlin-dentists
```

Open `output/berlin-dentists/places.csv`. You also get JSON, a report, and a page cache. Rerun the same command to resume; cached pages are free. Use a new output directory for fresh results or a changed query.

## Search many locations

Repeat `--location`, or supply a CSV with `location,country` and optional `language`:

```bash
python3 skills/google-maps-scraper/scripts/scrape.py \
  --query 'coffee shop' --locations-file examples/locations.csv \
  --max-pages 3 --max-requests 30 --output output/coffee
```

CSV locations can be cities, neighborhoods, or postal codes. Leading zeros are preserved. Each row can have its own country and language. Duplicate queries are removed before requests are made. The example is a small DACH pilot, not a complete postal-code database. Bring your own licensed location list for broader coverage.

## Costs and limits

The CLI uses `POST https://google.serper.dev/places` to retrieve Google Maps business listings. It does not call `/maps` for detail enrichment or `/reviews`.

A successful `/places` page uses one credit in the workflow this tool was built from. Pages commonly contain 10 results; the tool stops a query on a short page or at `--max-pages` (default 3). Check current endpoint billing in your Serper dashboard.

[Serper pricing](https://serper.dev/), checked October 26, 2026: Starter is $50 for 50,000 credits ($1/1,000); Standard is $375 for 500,000 ($0.75/1,000), excluding tax. Serper advertises 2,500 free queries. Prices and offers can change.

For example, 100 locations × 3 pages is at most 300 page requests before retries: about $0.30 of Starter credits at one credit per page. That is usage value from a prepaid pack, not the minimum purchase. Unique businesses may be much fewer than returned rows because neighboring searches overlap.

- `--max-requests` defaults to 30 and caps **every HTTP attempt, including retries, per invocation**. It resets when you rerun the command. It is not an account-wide or dollar budget.
- Up to two retries for rate limits, temporary server errors and network failures, with backoff. Authentication errors stop immediately.
- Calls are sequential, spaced by at least 0.5 seconds. This favors predictable costs and easy recovery over maximum throughput.
- Each successful page is committed to a local SQLite cache. A crash after the provider processes a request but before the local commit can still cause a repeated charge on resume.
- Partial runs export saved results and exit with code 2. `report.json` says `partial`; rerun the same command to continue.
- Do not run two processes against the same output directory at once.

## What you get

| File | Contents |
|---|---|
| `places.csv` | Business name, category, address, phone, website, domain, ratings, coordinates, CID, Maps link, source queries/pages |
| `places.json` | Same normalized records; CIDs are strings and phone values are unchanged |
| `report.json` | Completion status, page and request counts, duplicates, unique places, queries that hit the page cap |
| `config.json` | Exact search configuration; prevents mixing different runs |
| `cache.sqlite3` | Raw successful pages for resuming |

Deduplication uses CID, then place ID, then name + address. Listings without those identifiers are kept conservatively. Branches are not merged just because they share a website. CSV formula-like text is prefixed with an apostrophe for safer spreadsheet opening; use JSON for unchanged values. Import CID columns as text in spreadsheets to preserve all digits.

This is search-based discovery, **not an exhaustive census of Google Maps**. Broad queries can miss businesses; subdivide into neighborhoods/postal codes and inspect relevance. A full final page is flagged in the report. A short page is a stopping heuristic, not proof of complete coverage. Country and location terms bias search rather than enforce geographic boundaries. Fields may be missing. Listings do not include owner emails, and results are not automatically qualified or ready for outreach.

## Use as an agent skill

The self-contained skill lives at [`skills/google-maps-scraper`](skills/google-maps-scraper). Copy that whole directory into your agent's skills directory. For Codex:

```bash
mkdir -p ~/.codex/skills
cp -R skills/google-maps-scraper ~/.codex/skills/
```

Then ask: “Use google-maps-scraper to find dentists in Berlin with Serper. Start with a dry run and cap the pilot at 10 requests.” The script is included inside the skill, so no separate package is needed. Other agents that support `SKILL.md` can use the same folder.

## How this fits GTM Adviser

This repo is a standalone, MIT-licensed building block. [Agentic GTM](https://github.com/gtmadviser/agentic-gtm) provides broader GTM workflows; it does not currently include a Serper adapter. This CSV can be reviewed and mapped into another workflow, but automatic Agentic GTM import is not implemented here.

The implementation generalizes our category-by-location discovery work: pagination, exact CIDs, deduplication, request limits, and resume. No customer results, private account configuration, or application-specific taxonomy are included. Eric's [Google Maps list-builder skill](https://github.com/elnumae/ericscoldoutboundskills/tree/main/skills/google-maps-list-builder) informed the approachable query/location workflow; that skill uses RapidAPI. No code or datasets were copied from it.

## Develop and adapt

```bash
python3 -m unittest discover -s tests -v
python3 skills/google-maps-scraper/scripts/scrape.py --help
```

Tests use synthetic data and mocked HTTP, not your credits. Open an issue or pull request for improvements. Keep changes focused and tests offline; never attach API keys or private exports. Use the data in accordance with applicable provider terms and your use case's requirements.

## License

[MIT](LICENSE) covers this repository's code, documentation, and skill. You can use, modify, and redistribute them, including commercially, with the license notice. The license does not grant rights to third-party search results or location datasets.
