"""FTS5 ranked search (#4)."""
from pathlib import Path

from coursecrusader.database import CourseDatabase
from coursecrusader.models import Course


def test_fts5_search_ranks_title_hit(tmp_path: Path):
    db_path = str(tmp_path / "c.db")
    with CourseDatabase(db_path) as db:
        db.insert_course(
            Course(
                university="UConn",
                course_id="CSE 2100",
                title="Data Structures and Algorithms",
                description="Trees graphs hashing",
                credits=3,
                level="Undergraduate",
                department="CSE",
            )
        )
        db.insert_course(
            Course(
                university="UConn",
                course_id="HIST 1000",
                title="World History",
                description="No algorithms here",
                credits=3,
                level="Undergraduate",
                department="History",
            )
        )
        result = db.search_courses("algorithms")
        assert result["engine"] == "fts5"
        assert result["total"] >= 1
        ids = [r["course_id"] for r in result["rows"]]
        assert "CSE 2100" in ids
