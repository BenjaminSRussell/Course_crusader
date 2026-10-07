# Course catalog SQLite schema (#3)

Durable store used by `CourseDatabase` (`courses.db` by default).

## Tables

### `institutions`
| column | notes |
|---|---|
| id | PK |
| slug | unique short key (e.g. `uconn`) |
| name | display name |
| country | default `US` |
| created_at | ISO-8601 |

### `courses`
Cross-university rows. **Dedupe key:** `UNIQUE(university, course_id)`.

| column | notes |
|---|---|
| university | institution label (matches scraper `university`) |
| course_id | normalized code e.g. `CSE 2100` |
| title, description, credits, level, department | required catalog fields |
| prerequisites_*, corequisites_json, offerings_json | optional |
| catalog_url, last_updated, notes | provenance |

### `source_urls`
| column | notes |
|---|---|
| university + url | unique |
| course_id, kind, last_seen | optional |

### `scrape_metadata`
Per-run counts (`courses_added` / `updated` / `removed`).

## CLI

```bash
coursecrusader scrape -s uconn -d courses.db   # SqlitePipeline upserts
coursecrusader export -d courses.db -o courses.parquet
```

## Dedup demo

Inserting the same `(university, course_id)` twice updates in place; the same
`course_id` at two universities remains two rows.
