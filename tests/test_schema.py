"""
Tests for JSON schema validation.
"""

import pytest
import jsonschema

from coursecrusader.schema import COURSE_SCHEMA, validate_course_schema


class TestSchema:
    """Tests for the course JSON schema."""

    def test_schema_is_valid(self):
        """Test that the schema itself is valid JSON Schema."""
        assert validate_course_schema()

        jsonschema.Draft7Validator.check_schema(COURSE_SCHEMA)

    def test_schema_has_required_fields(self):
        """Test that schema defines all required fields."""
        required = COURSE_SCHEMA.get('required', [])

        assert 'university' in required
        assert 'course_id' in required
        assert 'title' in required
        assert 'description' in required
        assert 'credits' in required
        assert 'level' in required
        assert 'department' in required

    def test_validate_valid_course(self):
        """Test validating a valid course against schema."""
        course_data = {
            'university': 'UConn',
            'course_id': 'CSE 2100',
            'title': 'Data Structures',
            'description': 'Introduction to data structures and algorithms',
            'credits': 3,
            'level': 'Undergraduate',
        jsonschema.validate(course_data, COURSE_SCHEMA)

    def test_validate_missing_required_field(self):
        """Test that validation fails for missing required fields."""
        course_data = {
            'university': 'UConn',
            'course_id': 'CSE 2100',
            'description': 'Test',
            'credits': 3,
            'level': 'Undergraduate',
            'department': 'CSE'
        }

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(course_data, COURSE_SCHEMA)

    def test_validate_invalid_level(self):
        """Test that validation fails for invalid level enum."""
        course_data = {
            'university': 'UConn',
            'course_id': 'CSE 2100',
            'title': 'Test',
            'description': 'Test',
            'credits': 3,
            'level': 'InvalidLevel',  # Not in enum
            'department': 'CSE'
        }

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(course_data, COURSE_SCHEMA)

    def test_validate_with_prerequisites(self):
        """Test validating course with structured prerequisites."""
        course_data = {
            'university': 'UConn',
            'course_id': 'CSE 2100',
            'title': 'Data Structures',
            'description': 'Test',
            'credits': 3,
            'level': 'Undergraduate',
            'department': 'CSE',
            'prerequisites': {
                'and': ['CSE 1010', {'or': ['MATH 1131Q', 'MATH 1151Q']}]
            },
            'prerequisites_text': 'CSE 1010 and (MATH 1131Q or MATH 1151Q)',
            'prerequisites_parsed': True
        }

        jsonschema.validate(course_data, COURSE_SCHEMA)
