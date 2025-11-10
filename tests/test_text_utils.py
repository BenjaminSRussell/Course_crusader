"""
Tests for text parsing utilities.
"""

import pytest

from coursecrusader.parsers.text_utils import (
    clean_text,
    normalize_whitespace,
    fix_broken_lines,
    extract_credits,
    extract_department
)


class TestTextCleaning:
    """Tests for text cleaning functions."""

    def test_normalize_whitespace(self):
        """Test normalizing whitespace."""
        assert normalize_whitespace("  hello   world  ") == "hello world"
        assert normalize_whitespace("hello\n\nworld") == "hello world"
        assert normalize_whitespace("hello\tworld") == "hello world"

    def test_fix_broken_lines(self):
        """Test fixing broken lines in PDF text."""
        text = "This is a sen-\ntence"
        assert "sentence" in fix_broken_lines(text) or "sen- tence" in fix_broken_lines(text)

    def test_clean_text(self):
        """Test complete text cleaning."""
        text = "  Hello  &nbsp; world  "
        result = clean_text(text)

        assert "Hello" in result
        assert "world" in result
        assert "&nbsp;" not in result


class TestCreditExtraction:
    """Tests for credit hour extraction."""

    def test_extract_credits_basic(self):
        """Test extracting basic credit numbers."""
        assert extract_credits("3 credits") == 3
        assert extract_credits("4 cr.") == 4
        assert extract_credits("(3)") == 3

    def test_extract_credits_decimal(self):
        """Test extracting decimal credits."""
        assert extract_credits("3.5 credits") == 3.5
        assert extract_credits("1.5 cr") == 1.5

    def test_extract_credits_range(self):
        """Test extracting credit ranges."""
        result = extract_credits("3-4 credits")
        assert result == "3-4"

    def test_extract_credits_variable(self):
        """Test extracting variable credits."""
        assert extract_credits("variable credit") == "variable"
        assert extract_credits("credits vary") == "variable"

    def test_extract_credits_none(self):
        """Test when no credits found."""
        assert extract_credits("no credits here") is None
        assert extract_credits("") is None


class TestDepartmentExtraction:
    """Tests for department name extraction."""

    def test_extract_from_course_id(self):
        """Test extracting department from course ID."""
        result = extract_department("", "CSE 2100")
        assert result == "CSE"

        result = extract_department("", "MATH 1131Q")
        assert result == "MATH"

    def test_extract_from_text(self):
        """Test extracting department from text."""
        text = "Department of Computer Science"
        result = extract_department(text)
        assert "Computer Science" in result

        text = "Offered by: Mathematics"
        result = extract_department(text)
        assert "Mathematics" in result
