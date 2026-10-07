# Course Crusader

Unified university course-catalog scraper → JSONL/JSON/CSV, with optional SQLite import and scheduled refresh.

## Install (clean venv)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
# or: pip install -r requirements.txt
coursecrusader --help
```

## Quickstart

```bash
# List scrapers (stub vs live varies by school)
coursecrusader list

# Scrape one school (writes {school}_courses.jsonl by default)
coursecrusader scrape --school uconn
coursecrusader scrape -s uconn -f json -o data/uconn.json --limit 50

# Search / DB helpers (see CLI --help for import-db and search if enabled)
coursecrusader --help
```

Stub scrapers hit safe fixtures / httpbin-style endpoints; live catalogs hit real university sites — check scraper readiness before unattended runs.

## Automated refresh

```bash
python scripts/automated_refresh.py --help
# Example cron: scripts/crontab.example
crontab scripts/crontab.example   # edit paths first
```

## Docs / schema

- Package: `coursecrusader/` (CLI, scrapers, pipelines, database)
- Cron example: [`scripts/crontab.example`](scripts/crontab.example)
- Tests: `pytest`

## License

MIT — see `LICENSE`.


## Scraper readiness

See [docs/SCRAPER_STATUS.md](docs/SCRAPER_STATUS.md) (regenerate with `coursecrusader status --write`). `coursecrusader list` shows READY vs STUB.

## Politeness (#12)

`ROBOTSTXT_OBEY=True` with Scrapy `RobotsTxtMiddleware`. Default `DOWNLOAD_DELAY=1.0`; schools override via scraper `custom_settings` (e.g. UConn `1.5`).
`PolitenessLoggingMiddleware` logs robots skips and effective delay.

## Data-visualizer handoff

Export SQLite catalogs to Parquet:

```bash
pip install pyarrow
coursecrusader export -d courses.db -o courses.parquet
```

See [docs/PARQUET_EXPORT.md](docs/PARQUET_EXPORT.md).

## SQLite persistence (#9)

Scrapes upsert into SQLite via `SqlitePipeline` (default `courses.db`):

```bash
coursecrusader scrape -s uconn -d courses.db
COURSECRUSADER_DB_PATH=/tmp/courses.db coursecrusader scrape -s uconn
```

Re-scrapes upsert on `(university, course_id)` and append a `scrape_metadata` row.

## Storage / dedupe (#3)

SQLite catalog (`courses.db`) uses `UNIQUE(university, course_id)` so the same
code at two schools stays two rows while re-scrapes upsert. See
[docs/CATALOG_SCHEMA.md](docs/CATALOG_SCHEMA.md).

## Incremental refresh (#6)

```bash
coursecrusader refresh -u UConn -i uconn_courses.jsonl -d courses.db
```

Uses a SHA-256 snapshot of the input file; unchanged content is skipped.

## Querying the catalog (#4)

```bash
coursecrusader search "linear algebra" -d courses.db
coursecrusader search "calculus" -u MIT
coursecrusader explore -d courses.db   # FastAPI UI — pip install fastapi uvicorn
```

Search uses SQLite **FTS5** (ranked); falls back to LIKE if needed.

