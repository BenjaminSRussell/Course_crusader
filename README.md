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
