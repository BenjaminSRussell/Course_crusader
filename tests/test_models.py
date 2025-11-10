"""
Tests for course data models.
"""

import pytest
from datetime import datetime

from coursecrusader.models import Course, CatalogMetadata


class TestCourse:
    """Tests for the Course model."""

    def test_create_basic_course(self):
        """Test creating a basic course with required fields."""
        course = Course(
            university="UConn",
            course_id="CSE 2100",
            title="Data Structures",
            description="Introduction to data structures and algorithms",
            credits=3,
            level="Undergraduate",
            department="Computer Science & Engineering"
        )

        assert course.university == "UConn"
        assert course.course_id == "CSE 2100"
        assert course.title == "Data Structures"
        assert course.credits == 3
        assert course.level == "Undergraduate"

    def test_course_id_normalization(self):
        """Test that course IDs are normalized correctly."""
        # Without space
        course1 = Course(
            university="Test",
            course_id="CSE2100",
            title="Test",
            description="Test",
            credits=3,
            level="Undergraduate",
            department="Test"
        )
        assert course1.course_id == "CSE 2100"

        # With hyphen
        course2 = Course(
            university="Test",
            course_id="CSE-2100",
            title="Test",
            description="Test",
            credits=3,
            level="Undergraduate",
            department="Test"
        )
        assert course2.course_id == "CSE 2100"

        # Multiple spaces
        course3 = Course(
            university="Test",
            course_id="CSE  2100",
            title="Test",
            description="Test",
            credits=3,
            level="Undergraduate",
            department="Test"
        )
        assert course3.course_id == "CSE 2100"

    def test_infer_level(self):
        """Test level inference from course ID."""
        assert Course.infer_level("CSE 1010") == "Undergraduate"
        assert Course.infer_level("CSE 2100") == "Undergraduate"
        assert Course.infer_level("CSE 4999") == "Undergraduate"
        assert Course.infer_level("CSE 5100") == "Graduate"
        assert Course.infer_level("CSE 6000") == "Graduate"
        assert Course.infer_level("ABC") == "Unknown"

    def test_validation_success(self):
        """Test validation of a valid course."""
        course = Course(
            university="UConn",
            course_id="CSE 2100",
            title="Data Structures",
            description="Introduction to data structures",
            credits=3,
            level="Undergraduate",
            department="CSE"
        )

        is_valid, errors = course.validate()
        assert is_valid
        assert len(errors) == 0

    def test_validation_missing_fields(self):
        """Test validation catches missing required fields."""
        course = Course(
            university="",  # Empty
            course_id="CSE 2100",
            title="",  # Empty
            description="Test",
            credits=3,
            level="Undergraduate",
            department="CSE"
        )

        is_valid, errors = course.validate()
        assert not is_valid
        assert len(errors) > 0
        assert any("university" in err.lower() for err in errors)

    def test_validation_invalid_course_id(self):
        """Test validation catches invalid course ID format."""
        course = Course(
            university="UConn",
            course_id="Invalid-123",  # Invalid format
            title="Test",
            description="Test",
            credits=3,
            level="Undergraduate",
            department="CSE"
        )

        is_valid, errors = course.validate()
        assert not is_valid
        assert any("course_id" in err.lower() for err in errors)

    def test_to_dict(self):
        """Test converting course to dictionary."""
        course = Course(
            university="UConn",
            course_id="CSE 2100",
            title="Data Structures",
            description="Test",
            credits=3,
            level="Undergraduate",
            department="CSE",
            prerequisites={"and": ["CSE 1010"]},
            prerequisites_text="CSE 1010",
            prerequisites_parsed=True
        )

        data = course.to_dict()

        assert isinstance(data, dict)
        assert data['university'] == "UConn"
        assert data['course_id'] == "CSE 2100"
        assert data['prerequisites'] == {"and": ["CSE 1010"]}
        assert 'last_updated' in data

    def test_last_updated_auto_set(self):
        """Test that last_updated is automatically set."""
        course = Course(
            university="UConn",
            course_id="CSE 2100",
            title="Test",
            description="Test",
            credits=3,
            level="Undergraduate",
            department="CSE"
        )

        assert course.last_updated is not None
        assert 'T' in course.last_updated  # ISO format


class TestCatalogMetadata:
    """Tests for CatalogMetadata model."""

    def test_create_metadata(self):
        """Test creating catalog metadata."""
        metadata = CatalogMetadata(
            university="UConn",
            scrape_date=datetime.utcnow().isoformat(),
            total_courses=1000,
            successful_parses=950,
            failed_parses=50,
            catalog_url="https://example.com",
            scraper_version="0.1.0"
        )

        assert metadata.university == "UConn"
        assert metadata.total_courses == 1000
        assert metadata.successful_parses == 950

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        metadata = CatalogMetadata(
            university="UConn",
            scrape_date=datetime.utcnow().isoformat(),
            total_courses=1000,
            successful_parses=900,
            failed_parses=100,
            catalog_url="https://example.com",
            scraper_version="0.1.0"
        )

        assert metadata.success_rate == 90.0

    def test_success_rate_zero_division(self):
        """Test success rate with no parses."""
        metadata = CatalogMetadata(
            university="UConn",
            scrape_date=datetime.utcnow().isoformat(),
            total_courses=0,
            successful_parses=0,
            failed_parses=0,
            catalog_url="https://example.com",
            scraper_version="0.1.0"
        )

        assert metadata.success_rate == 0.0
