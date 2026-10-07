"""Parquet export row-count parity (#11)."""
from pathlib import Path

import pyarrow.parquet as pq

from coursecrusader.database import CourseDatabase
from coursecrusader.models import Course


def test_export_parquet_row_count(tmp_path: Path):
    db_path = tmp_path / "courses.db"
    out = tmp_path / "courses.parquet"
    with CourseDatabase(str(db_path)) as db:
        db.insert_course(
            Course(
                university="UConn",
                course_id="CSE 2100",
                title="Data Structures",
                description="Trees and graphs",
                credits=3,
                level="Undergraduate",
                department="CSE",
            )
        )
        db.insert_course(
            Course(
                university="MIT",
                course_id="EECS 6006",
                title="Intro Algorithms",
                description="Algo",
                credits=12,
                level="Undergraduate",
                department="EECS",
            )
        )
        n = db.export_to_parquet(str(out))
        assert n == 2
    table = pq.read_table(out)
    assert table.num_rows == 2
    assert "university" in table.column_names
