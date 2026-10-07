"""Tests for corequisite and offerings query helpers."""

import tempfile
from pathlib import Path

import pytest

from coursecrusader.database import CourseDatabase
from coursecrusader.models import Course


def _course(**kwargs) -> Course:
    base = dict(
        university="TestU",
        course_id="CS999",
        title="T",
        description="desc",
        credits=3,
        level="Undergraduate",
        department="CS",
    )
    base.update(kwargs)
    return Course(**base)


def test_courses_with_corequisite_exact_json_not_freetext():
    with tempfile.TemporaryDirectory() as tmp:
        db = CourseDatabase(str(Path(tmp) / "t.db"))
        db.insert_course(
            _course(
                course_id="CS200",
                title="With coreq",
                corequisites=["CSE 2100", "MATH 100"],
                description="Mentions CSE 2100 in free text too",
            )
        )
        db.insert_course(
            _course(
                course_id="CS201",
                title="Freetext only",
                description="Students should also know CSE 2100",
                corequisites=None,
            )
        )
        db.insert_course(
            _course(
                course_id="CS202",
                title="Other coreq",
                corequisites=["CSE 9999"],
            )
        )
        # Corrupt JSON row via raw SQL
        db.conn.execute(
            "UPDATE courses SET corequisites_json = '{not-json' WHERE course_id = ?",
            ("CS 202",),
        )
        db.conn.commit()

        result = db.courses_with_corequisite("CSE 2100")
        ids = {r["course_id"] for r in result["rows"]}
        assert "CS 200" in ids or "CS200" in ids or any("200" in i for i in ids)
        assert not any("201" in r["course_id"] for r in result["rows"])
        assert result["skipped_invalid"] >= 1
        db.close()


def test_courses_offered_in_exact_term():
    with tempfile.TemporaryDirectory() as tmp:
        db = CourseDatabase(str(Path(tmp) / "t.db"))
        db.insert_course(_course(course_id="CS301", offerings=["Fall", "Spring"]))
        db.insert_course(_course(course_id="CS302", offerings=["Year-round"]))
        db.insert_course(_course(course_id="CS303", offerings=["Summer"]))
        db.conn.execute(
            "UPDATE courses SET offerings_json = 'not-a-list' WHERE course_id LIKE ?",
            ("%303%",),
        )
        db.conn.commit()

        fall = db.courses_offered_in("Fall")
        fall_ids = {r["course_id"] for r in fall["rows"]}
        assert any("301" in i for i in fall_ids)
        assert not any("302" in i for i in fall_ids)  # Year-round != Fall

        with pytest.raises(ValueError):
            db.courses_offered_in("Autumn")

        # Invalid JSON rows are skipped while scanning any term
        assert fall["skipped_invalid"] >= 1
        summer = db.courses_offered_in("Summer")
        assert not any("303" in r["course_id"] for r in summer["rows"])
        assert summer["skipped_invalid"] >= 1
        db.close()
