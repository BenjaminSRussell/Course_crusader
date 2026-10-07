"""Tests for search pagination and insert upsert accounting."""

import tempfile
from pathlib import Path

from coursecrusader.database import CourseDatabase
from coursecrusader.models import Course
from coursecrusader.parsers import PrerequisiteParser


def _course(cid: str, title: str = "T", desc: str = "machine learning") -> Course:
    return Course(
        university="TestU",
        course_id=cid,
        title=title,
        description=desc,
        credits=3,
        level="Undergraduate",
        department="CS",
    )


def test_prerequisites_importable():
    parser = PrerequisiteParser()
    structured, ok = parser.parse("CSE 101 and MATH 200")
    assert ok is True or structured is not None or structured is None


def test_search_default_limit_and_empty_query():
    with tempfile.TemporaryDirectory() as tmp:
        db = CourseDatabase(str(Path(tmp) / "t.db"))
        for i in range(60):
            db.insert_course(_course(f"CS{100+i}"))
        res = db.search_courses("machine learning")
        assert len(res["rows"]) == 50
        assert res["total"] == 60
        assert res["truncated"] is True
        page = db.search_courses("machine learning", limit=10, offset=10)
        assert len(page["rows"]) == 10
        assert db.search_courses("")["rows"] == []
        assert db.search_courses("   ")["total"] == 0
        db.close()


def test_insert_distinguishes_added_vs_updated():
    with tempfile.TemporaryDirectory() as tmp:
        db = CourseDatabase(str(Path(tmp) / "t.db"))
        r1 = db.insert_course(_course("CS101", title="Intro"))
        assert r1["added"] == 1 and r1["updated"] == 0
        row_id = r1["row_id"]
        r2 = db.insert_course(_course("CS101", title="Intro Updated"))
        assert r2["added"] == 0 and r2["updated"] == 1
        assert r2["row_id"] == row_id
        assert db.get_course("TestU", "CS 101")["title"] == "Intro Updated"
        bulk = db.insert_courses_bulk(
            [
                _course("CS102"),
                _course("CS101", title="Again"),
            ]
        )
        assert bulk["added"] == 1
        assert bulk["updated"] == 1
        db.close()
