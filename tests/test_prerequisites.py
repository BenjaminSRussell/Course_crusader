"""
Tests for prerequisite parsing.
"""

import pytest

from coursecrusader.parsers.prerequisites import PrerequisiteParser


class TestPrerequisiteParser:
    """Tests for the PrerequisiteParser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = PrerequisiteParser()

    def test_parse_simple_and(self):
        """Test parsing simple AND prerequisites."""
        text = "CSE 1010 and CSE 1729"
        result, success = self.parser.parse(text)

        assert success
        assert result == {"and": ["CSE 1010", "CSE 1729"]}

    def test_parse_simple_or(self):
        """Test parsing simple OR prerequisites."""
        text = "MATH 1131Q or MATH 1151Q"
        result, success = self.parser.parse(text)

        assert success
        assert result == {"or": ["MATH 1131Q", "MATH 1151Q"]}

    def test_parse_nested_prerequisites(self):
        """Test parsing nested prerequisites with parentheses."""
        text = "CSE 2100 and (MATH 2210Q or MATH 2410Q)"
        result, success = self.parser.parse(text)

        assert success
        assert result is not None
        assert "and" in result
        assert any(isinstance(item, dict) and "or" in item for item in result["and"])

    def test_parse_single_course(self):
        """Test parsing single prerequisite course."""
        text = "CSE 1010"
        result, success = self.parser.parse(text)

        assert success
        assert result == {"and": ["CSE 1010"]}

    def test_parse_empty_string(self):
        """Test parsing empty prerequisite string."""
        text = ""
        result, success = self.parser.parse(text)

        assert success
        assert result is None

    def test_parse_no_courses(self):
        """Test parsing text with no course codes."""
        text = "Permission of instructor required"
        result, success = self.parser.parse(text)

        # No courses found, but text exists
        assert not success or result is None

    def test_extract_courses(self):
        """Test extracting course codes from text."""
        text = "CSE 1010 and MATH 2210Q are required"
        courses = self.parser._extract_courses(text)

        assert "CSE 1010" in courses
        assert "MATH 2210Q" in courses

    def test_extract_courses_various_formats(self):
        """Test extracting courses in various formats."""
        # With space
        assert self.parser._extract_courses("CSE 2100") == ["CSE 2100"]

        # Without space
        assert self.parser._extract_courses("CSE2100") == ["CSE 2100"]

        # With hyphen
        assert self.parser._extract_courses("CSE-2100") != []

        # Multiple courses
        courses = self.parser._extract_courses("CSE 1010, CSE 1729, MATH 1131Q")
        assert len(courses) >= 3

    def test_extract_corequisites(self):
        """Test extracting corequisite courses."""
        text = "Corequisite: CSE 1010"
        result = self.parser.extract_corequisites(text)

        assert result is not None
        assert "CSE 1010" in result

    def test_extract_corequisites_plural(self):
        """Test extracting multiple corequisites."""
        text = "Corequisites: CSE 1010 and CSE 1729"
        result = self.parser.extract_corequisites(text)

        assert result is not None
        assert "CSE 1010" in result
        assert "CSE 1729" in result

    def test_non_course_requirements(self):
        """Test identifying non-course requirements."""
        texts = [
            "Junior standing required",
            "Permission of instructor",
            "Minimum GPA of 3.0",
            "Open only to majors",
        ]

        for text in texts:
            reqs = self.parser._extract_non_course_requirements(text)
            assert len(reqs) > 0

    def test_complex_prerequisites(self):
        """Test parsing complex prerequisite statements."""
        # This might fail initially - that's expected
        # We flag it as unparsed rather than return wrong data
        text = "CSE 1010 and CSE 1729 or MATH 2210Q and junior standing"
        result, success = self.parser.parse(text)

        # Complex case - might not parse successfully
        # But it should not crash
        assert result is not None or not success
