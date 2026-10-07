"""SqlitePipeline upserts + scrape_metadata (#9)."""
from pathlib import Path
from unittest.mock import MagicMock

from coursecrusader.models import Course
from coursecrusader.pipelines import SqlitePipeline
from coursecrusader.database import CourseDatabase


def test_sqlite_pipeline_upserts(tmp_path: Path):
    db_path = str(tmp_path / "courses.db")
    crawler = MagicMock()
    crawler.settings.get.return_value = db_path
    pipe = SqlitePipeline.from_crawler(crawler)
    spider = MagicMock()
    spider.university = "UConn"
    spider.name = "uconn"
    spider.logger = MagicMock()

    pipe.open_spider(spider)
    c1 = Course(
        university="UConn",
        course_id="CSE 2100",
        title="Data Structures",
        description="Trees",
        credits=3,
        level="Undergraduate",
        department="CSE",
    )
    pipe.process_item(c1, spider)
    c1.title = "Data Structures & Algorithms"
    pipe.process_item(c1, spider)
    pipe.close_spider(spider)

    with CourseDatabase(db_path) as db:
        row = db.get_course("UConn", "CSE 2100")
        assert row is not None
        assert "Algorithms" in row["title"]
        cur = db.conn.cursor()
        cur.execute("SELECT courses_added, courses_updated FROM scrape_metadata")
        meta = cur.fetchone()
        assert meta is not None
        assert meta[0] + meta[1] >= 1
