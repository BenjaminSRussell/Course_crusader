# Parquet export schema (#11)

Columns mirror the `courses` SQLite table (without `id`):

| column | type |
|---|---|
| university | string |
| course_id | string |
| title | string |
| description | string |
| credits | string |
| level | string |
| department | string |
| prerequisites_text | string |
| prerequisites_json | string (JSON) |
| prerequisites_parsed | bool |
| corequisites_json | string (JSON) |
| restrictions | string |
| offerings_json | string (JSON) |
| catalog_url | string |
| last_updated | string |
| notes | string |

```bash
coursecrusader export -d courses.db -f parquet -o courses.parquet
coursecrusader export -d courses.db -o out/ --partition-by-university
```

DuckDB: `SELECT count(*) FROM 'courses.parquet';`
