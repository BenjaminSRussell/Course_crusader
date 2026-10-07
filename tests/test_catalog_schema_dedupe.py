"""Catalog schema + cross-university dedupe (#3)."""
from pathlib import Path

from coursecrusader.database import CourseDatabase
from coursecrusader.models import Course


def _course(university: str, course_id: str, title: str) -> Course:
    return Course(
        university=university,
        course_id=course_id,
        title=title,
        description="desc",
        credits=3,
        level="Undergraduate",
        department="CSE",
    )


def test_institutions_and_cross_uni_dedupe(tmp_path: Path):
    db_path = str(tmp_path / "courses.db")
    with CourseDatabase(db_path) as db:
        uconn_id = db.upsert_institution("uconn", "University of Connecticut")
        mit_id = db.upsert_institution("mit", "MIT")
        assert uconn_id != mit_id

        r1 = db.insert_course(_course("UConn", "CSE 2100", "Data Structures"))
        r2 = db.insert_course(_course("UConn", "CSE 2100", "Data Structures II"))
        r3 = db.insert_course(_course("MIT", "CSE 2100", "Intro Algorithms"))

        assert r1["added"] == 1
        assert r2["updated"] == 1
        assert r3["added"] == 1

        assert db.get_course("UConn", "CSE 2100")["title"] == "Data Structures II"
        assert db.get_course("MIT", "CSE 2100")["title"] == "Intro Algorithms"

        cur = db.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM courses")
        assert cur.fetchone()[0] == 2

        db.record_source_url("UConn", "https://catalog.uconn.edu/cse2100", "CSE 2100")
        cur.execute("SELECT COUNT(*) FROM source_urls")
        assert cur.fetchone()[0] == 1
