"""
JSON Schema definition for unified course catalog data.

This schema ensures all university course data conforms to a consistent structure,
regardless of the source institution's catalog format.
"""

COURSE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Course",
    "description": "Unified schema for university course catalog data",
    "type": "object",
    "required": [
        "university",
        "course_id",
        "title",
        "description",
        "credits",
        "level",
        "department"
    ],
    "properties": {
        "university": {
            "type": "string",
            "description": "University/institution identifier (e.g., 'UConn', 'MIT')"
        },
        "course_id": {
            "type": "string",
            "description": "Course code/identifier (e.g., 'CSE 2100', 'CS 101')",
            "pattern": "^[A-Z]{2,6}\\s*\\d{3,4}[A-Z]?$"
        },
        "title": {
            "type": "string",
            "description": "Course title"
        },
        "description": {
            "type": "string",
            "description": "Full course description"
        },
        "credits": {
            "oneOf": [
                {"type": "number"},
                {"type": "string", "pattern": "^\\d+(-\\d+)?$"}
            ],
            "description": "Credit hours (number or range like '3-4')"
        },
        "level": {
            "type": "string",
            "enum": ["Undergraduate", "Graduate", "Professional", "Unknown"],
            "description": "Course level classification"
        },
        "department": {
            "type": "string",
            "description": "Department or academic unit offering the course"
        },
        "prerequisites": {
            "type": "object",
            "description": "Structured prerequisite requirements with logical operators",
            "properties": {
                "and": {
                    "type": "array",
                    "items": {
                        "oneOf": [
                            {"type": "string"},
                            {"$ref": "#/properties/prerequisites"}
                        ]
                    }
                },
                "or": {
                    "type": "array",
                    "items": {
                        "oneOf": [
                            {"type": "string"},
                            {"$ref": "#/properties/prerequisites"}
                        ]
                    }
                }
            }
        },
        "prerequisites_text": {
            "type": "string",
            "description": "Original prerequisite text as it appears in catalog"
        },
        "prerequisites_parsed": {
            "type": "boolean",
            "description": "Flag indicating if prerequisites were successfully parsed into structured form"
        },
        "corequisites": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Courses that must be taken concurrently"
        },
        "restrictions": {
            "type": "string",
            "description": "Enrollment restrictions (e.g., 'Junior standing required', 'Major only')"
        },
        "offerings": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["Fall", "Spring", "Summer", "Winter", "Year-round"]
            },
            "description": "Semesters/terms when course is typically offered"
        },
        "catalog_url": {
            "type": "string",
            "format": "uri",
            "description": "URL to the course's catalog page"
        },
        "last_updated": {
            "type": "string",
            "format": "date-time",
            "description": "Timestamp when this data was last scraped"
        },
        "notes": {
            "type": "string",
            "description": "Additional notes or parsing uncertainties"
        }
    }
}


def validate_course_schema():
    """
    Validate that the schema itself is well-formed.
    This is a sanity check for development.
    """
    try:
        import jsonschema
        # Ensure the schema is valid JSON Schema
        jsonschema.Draft7Validator.check_schema(COURSE_SCHEMA)
        return True
    except Exception as e:
        print(f"Schema validation error: {e}")
        return False


if __name__ == "__main__":
    # Test schema validity
    if validate_course_schema():
        print("Course schema is valid!")
        import json
        print(json.dumps(COURSE_SCHEMA, indent=2))
    else:
        print("Course schema has errors!")
