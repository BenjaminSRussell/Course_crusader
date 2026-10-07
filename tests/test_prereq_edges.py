"""Prerequisite edge table + cycle detection (#5)."""
from pathlib import Path
import json

from coursecrusader.database import CourseDatabase
from coursecrusader.models import Course


def test_rebuild_edges_and_export(tmp_path: Path):
    db_path = str(tmp_path / "c.db")
    with CourseDatabase(db_path) as db:
        db.insert_course(
            Course(
                university="UConn",
                course_id="CSE 1010",
                title="Intro",
                description="d",
                credits=3,
                level="Undergraduate",
                department="CSE",
            )
        )
        db.insert_course(
            Course(
                university="UConn",
                course_id="CSE 2100",
                title="DS",
                description="d",
                credits=3,
                level="Undergraduate",
                department="CSE",
                prerequisites={"and": ["CSE 1010"]},
                prerequisites_parsed=True,
            )
        )
        # store json column explicitly via update if needed
        cur = db.conn.cursor()
        cur.execute(
            "UPDATE courses SET prerequisites_json = ? WHERE course_id = ?",
            (json.dumps({"and": ["CSE 1010"]}), "CSE 2100"),
        )
        db.conn.commit()
        info = db.rebuild_prerequisite_edges("UConn")
        assert info["edges"] >= 1
        assert info["cycles"] == []
        g = json.loads(db.export_graph("CSE 2100", university="UConn", fmt="json"))
        assert any(e["from_course_id"] == "CSE 1010" for e in g["edges"])
        dot = db.export_graph("CSE 2100", university="UConn", fmt="dot")
        assert "CSE 1010" in dot and "->" in dot
