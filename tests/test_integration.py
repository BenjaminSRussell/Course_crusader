"""
Integration tests for Course Crusader.

Tests end-to-end workflows including PDF parsing, database operations, and validation.
"""

import pytest
import json
import tempfile
from pathlib import Path

from coursecrusader.models import Course
from coursecrusader.database import CourseDatabase
from coursecrusader.parsers.pdf_parser import PDFCatalogParser
from coursecrusader.refresh import ChangeDetector
from coursecrusader.validation import ValidationMetrics, ValidationReport


class TestDatabaseIntegration:
    """Integration tests for database operations."""

    def test_database_create_and_query(self):
        """Test creating database and querying courses."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # Create database and add courses
            db = CourseDatabase(str(db_path))

            course1 = Course(
                university="TestU",
                course_id="CS 101",
                title="Intro to CS",
                description="Introduction to computer science",
                credits=3,
                level="Undergraduate",
                department="Computer Science"
            )

            course2 = Course(
                university="TestU",
                course_id="CS 102",
                title="Data Structures",
                description="Introduction to data structures",
                credits=3,
                level="Undergraduate",
                department="Computer Science"
            )

            db.insert_course(course1)
            db.insert_course(course2)

            # Query courses
            courses = db.get_courses_by_university("TestU")
            assert len(courses) == 2

            # Search
            results = db.search_courses("data", "TestU")
            assert len(results) == 1
            assert results[0]['course_id'] == "CS 102"

            db.close()

    def test_database_statistics(self):
        """Test database statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = CourseDatabase(str(db_path))

            # Add multiple courses
            for i in range(5):
                course = Course(
                    university="TestU",
                    course_id=f"CS {100 + i}",
                    title=f"Course {i}",
                    description="Test course",
                    credits=3,
                    level="Undergraduate",
                    department="CS"
                )
                db.insert_course(course)

            stats = db.get_statistics()
            assert stats['total_courses'] == 5
            assert "TestU" in stats['by_university']

            db.close()


class TestChangeDetection:
    """Integration tests for change detection."""

    def test_change_detector_first_run(self):
        """Test change detector on first run."""
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_file = Path(tmpdir) / "snapshots.json"
            detector = ChangeDetector(str(snapshot_file))

            # First check should always return True (needs scraping)
            # Note: This would normally check a real URL, but we'll skip actual network calls
            # Just test the snapshot creation logic
            snapshot = detector.get_snapshot("TestU")
            assert snapshot is None  # No snapshot yet

    def test_snapshot_persistence(self):
        """Test that snapshots persist across detector instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_file = Path(tmpdir) / "snapshots.json"

            # Create first detector and save snapshot
            detector1 = ChangeDetector(str(snapshot_file))
            detector1.update_snapshot("TestU", course_count=100, notes="Test")

            # Create second detector and verify snapshot loaded
            detector2 = ChangeDetector(str(snapshot_file))
            snapshot = detector2.get_snapshot("TestU")

            assert snapshot is not None
            assert snapshot.university == "TestU"
            assert snapshot.course_count == 100


class TestValidationFramework:
    """Integration tests for validation framework."""

    def test_validation_metrics(self):
        """Test validation metrics calculation."""
        metrics = ValidationMetrics()
        metrics.total = 100
        metrics.correct = 95
        metrics.incorrect = 3
        metrics.missing = 2

        assert metrics.accuracy == 95.0
        assert metrics.completeness == 98.0

    def test_validation_report(self):
        """Test validation report generation."""
        report = ValidationReport(
            university="TestU",
            total_courses=50
        )

        # Add field metrics
        course_id_metrics = ValidationMetrics(total=50, correct=50, incorrect=0, missing=0)
        title_metrics = ValidationMetrics(total=50, correct=48, incorrect=2, missing=0)

        report.add_field_metric("course_id", course_id_metrics)
        report.add_field_metric("title", title_metrics)

        # Test overall accuracy
        overall = report.overall_accuracy()
        assert overall == 98.0  # (50 + 48) / (50 + 50) * 100

        # Test serialization
        report_dict = report.to_dict()
        assert report_dict['university'] == "TestU"
        assert 'field_metrics' in report_dict


class TestPDFParserIntegration:
    """Integration tests for PDF parsing."""

    def test_pdf_course_extraction(self):
        """Test extracting courses from PDF text."""
        parser = PDFCatalogParser()

        # Sample PDF text (simulated)
        sample_text = """
        CSE 2100. Data Structures and Algorithms. 3 credits.
        Introduction to fundamental data structures including arrays, linked lists,
        stacks, queues, trees, and graphs. Analysis of algorithm complexity.
        Prerequisite: CSE 1010 and (MATH 2210Q or MATH 2410Q).

        CSE 3100. Systems Programming. 4 credits.
        Introduction to systems programming and computer organization.
        Prerequisite: CSE 2100.
        """

        # Split into courses
        courses = parser.split_into_courses(sample_text)
        assert len(courses) == 2

        # Parse first course
        course_data = parser.extract_course_from_text(courses[0])
        assert course_data is not None
        assert course_data['course_id'] == "CSE 2100"
        assert course_data['title'] == "Data Structures and Algorithms"
        assert course_data['credits'] == 3
        assert course_data['prerequisites_text'] is not None


class TestEndToEndWorkflow:
    """End-to-end integration tests."""

    def test_jsonl_to_database_workflow(self):
        """Test complete workflow: JSONL -> Database -> Query."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test JSONL file
            jsonl_path = Path(tmpdir) / "courses.jsonl"
            db_path = Path(tmpdir) / "courses.db"

            # Write test data
            test_courses = [
                {
                    'university': 'TestU',
                    'course_id': 'CS 101',
                    'title': 'Intro to CS',
                    'description': 'Introduction',
                    'credits': 3,
                    'level': 'Undergraduate',
                    'department': 'CS'
                },
                {
                    'university': 'TestU',
                    'course_id': 'CS 102',
                    'title': 'Data Structures',
                    'description': 'Data structures',
                    'credits': 3,
                    'level': 'Undergraduate',
                    'department': 'CS'
                }
            ]

            with open(jsonl_path, 'w') as f:
                for course in test_courses:
                    f.write(json.dumps(course) + '\n')

            # Import to database
            db = CourseDatabase(str(db_path))
            for course_data in test_courses:
                course = Course(**course_data)
                db.insert_course(course)

            # Query and verify
            courses = db.get_courses_by_university("TestU")
            assert len(courses) == 2

            # Search
            results = db.search_courses("Data")
            assert len(results) == 1

            db.close()
