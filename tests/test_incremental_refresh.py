"""Incremental refresh skips unchanged snapshots (#6)."""
import json
from pathlib import Path

from coursecrusader.database import CourseDatabase


def test_second_refresh_skips_unchanged(tmp_path: Path):
    db_path = str(tmp_path / "c.db")
    fixture = tmp_path / "uconn.json"
    courses = [
        {
            "university": "UConn",
            "course_id": "CSE 1010",
            "title": "Intro",
            "description": "d",
            "credits": 3,
            "level": "Undergraduate",
            "department": "CSE",
        }
    ]
    fixture.write_text(json.dumps(courses))
    raw = fixture.read_bytes()
    import hashlib

    h = hashlib.sha256(raw).hexdigest()
    with CourseDatabase(db_path) as db:
        r1 = db.refresh_courses_from_dicts("UConn", courses, h, url="file://uconn.json")
        assert r1["skipped"] is False
        assert r1["added"] == 1
        r2 = db.refresh_courses_from_dicts("UConn", courses, h, url="file://uconn.json")
        assert r2["skipped"] is True
        # mutate
        courses[0]["title"] = "Intro CS"
        h2 = hashlib.sha256(json.dumps(courses).encode()).hexdigest()
        r3 = db.refresh_courses_from_dicts("UConn", courses, h2, url="file://uconn.json")
        assert r3["skipped"] is False
        assert r3["updated"] == 1
        assert db.get_course("UConn", "CSE 1010")["title"] == "Intro CS"
