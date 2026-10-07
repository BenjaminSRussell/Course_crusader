"""Tiny FastAPI explorer over CourseDatabase. Optional dep: fastapi, uvicorn."""

from __future__ import annotations

from pathlib import Path
from typing import Optional


def create_app(db_path: str = "courses.db"):
    try:
        from fastapi import FastAPI, Query
        from fastapi.responses import HTMLResponse
    except ImportError as e:  # pragma: no cover
        raise ImportError("pip install fastapi uvicorn to use the explorer") from e

    from coursecrusader.database import CourseDatabase

    app = FastAPI(title="Course Crusader Explorer", version="0.1.0")

    @app.get("/", response_class=HTMLResponse)
    def home():
        with CourseDatabase(db_path) as db:
            stats = db.get_statistics()
        unis = stats.get("by_university") or {}
        rows = "".join(
            f"<tr><td>{u}</td><td>{n}</td></tr>" for u, n in sorted(unis.items())
        )
        return f"""<!doctype html>
<html><head><title>Course Crusader</title>
<style>body{{font-family:system-ui;margin:2rem}} table{{border-collapse:collapse}}
td,th{{border:1px solid #ccc;padding:.4rem .8rem}}</style></head>
<body>
<h1>Course Crusader</h1>
<p>Total courses: <b>{stats.get('total_courses', 0)}</b></p>
<form action="/search" method="get">
  <input name="q" placeholder="search…" size="40"/>
  <button type="submit">Search</button>
</form>
<h2>Universities</h2>
<table><tr><th>University</th><th>Courses</th></tr>{rows}</table>
</body></html>"""

    @app.get("/search", response_class=HTMLResponse)
    def search(q: str = Query(""), university: Optional[str] = None, limit: int = 25):
        with CourseDatabase(db_path) as db:
            result = db.search_courses(q, university=university, limit=limit)
        items = "".join(
            f"<li><b>{r['university']} {r['course_id']}</b> — {r['title']}</li>"
            for r in result["rows"]
        )
        return f"""<!doctype html>
<html><head><title>Search</title></head><body style="font-family:system-ui;margin:2rem">
<p><a href="/">← home</a></p>
<h1>Results for {q!s}</h1>
<p>{result['total']} hits (engine={result.get('engine')})</p>
<ul>{items or '<li>none</li>'}</ul>
</body></html>"""

    @app.get("/api/stats")
    def api_stats():
        with CourseDatabase(db_path) as db:
            return db.get_statistics()

    @app.get("/api/search")
    def api_search(q: str = "", university: Optional[str] = None, limit: int = 25):
        with CourseDatabase(db_path) as db:
            return db.search_courses(q, university=university, limit=limit)

    return app


def main(db_path: str = "courses.db", host: str = "127.0.0.1", port: int = 8765):
    import uvicorn

    uvicorn.run(create_app(db_path), host=host, port=port)


if __name__ == "__main__":
    main()
