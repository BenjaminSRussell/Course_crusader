"""
Test suite for verifying course URL capture.

Ensures that catalog_url field is properly populated for all scrapers.
"""

import pytest
from coursecrusader.models import Course


class TestURLCapture:
    """Tests to verify course URLs are being captured."""

    def test_course_has_url_field(self):
        """Test that Course model includes catalog_url field."""
        course = Course(
            university="TestU",
            course_id="CS 101",
            title="Test Course",
            description="Test",
            credits=3,
            level="Undergraduate",
            department="CS",
            catalog_url="https://example.com/courses/cs-101"
        )

        assert course.catalog_url == "https://example.com/courses/cs-101"

    def test_course_url_in_dict_export(self):
        """Test that catalog_url is included when exporting to dict."""
        course = Course(
            university="TestU",
            course_id="CS 101",
            title="Test Course",
            description="Test",
            credits=3,
            level="Undergraduate",
            department="CS",
            catalog_url="https://example.com/courses/cs-101"
        )

        course_dict = course.to_dict()
        assert 'catalog_url' in course_dict
        assert course_dict['catalog_url'] == "https://example.com/courses/cs-101"

    def test_course_url_optional(self):
        """Test that catalog_url is optional (for backward compatibility)."""
        course = Course(
            university="TestU",
            course_id="CS 101",
            title="Test Course",
            description="Test",
            credits=3,
            level="Undergraduate",
            department="CS"
        )

        assert course.catalog_url is None

    def test_database_stores_url(self):
        """Test that database properly stores catalog URLs."""
        from coursecrusader.database import CourseDatabase
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = CourseDatabase(str(db_path))

            course = Course(
                university="TestU",
                course_id="CS 101",
                title="Test Course",
                description="Test",
                credits=3,
                level="Undergraduate",
                department="CS",
                catalog_url="https://catalog.testu.edu/cs-101"
            )

            db.insert_course(course)

            # Retrieve and verify
            retrieved = db.get_course("TestU", "CS 101")
            assert retrieved is not None
            assert retrieved['catalog_url'] == "https://catalog.testu.edu/cs-101"

            db.close()


class TestScraperURLCapture:
    """Test that scrapers properly set catalog URLs."""

    def test_base_scraper_includes_url(self):
        """Test that base scraper create_course includes URL parameter."""
        from coursecrusader.scrapers.base import BaseCourseScraper

        class TestScraper(BaseCourseScraper):
            name = "test"
            university = "Test University"
            start_urls = ['http://example.com']

            def parse(self, response):
                pass

        scraper = TestScraper()

        # Test create_course with catalog_url
        course = scraper.create_course(
            course_id="CS 101",
            title="Test",
            description="Test",
            credits=3,
            level="Undergraduate",
            department="CS",
            catalog_url="https://example.com/course/cs-101"
        )

        assert course.catalog_url == "https://example.com/course/cs-101"


def test_url_capture_in_jsonl_export():
    """Test that URLs are preserved in JSONL export."""
    import json
    import tempfile
    from pathlib import Path

    course = Course(
        university="TestU",
        course_id="CS 101",
        title="Test Course",
        description="Test",
        credits=3,
        level="Undergraduate",
        department="CS",
        catalog_url="https://catalog.testu.edu/cs-101"
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        jsonl_path = Path(tmpdir) / "test.jsonl"

        # Write course to JSONL
        with open(jsonl_path, 'w') as f:
            f.write(json.dumps(course.to_dict()) + '\n')

        # Read back and verify
        with open(jsonl_path, 'r') as f:
            loaded = json.loads(f.readline())

        assert 'catalog_url' in loaded
        assert loaded['catalog_url'] == "https://catalog.testu.edu/cs-101"
