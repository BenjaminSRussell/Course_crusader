"""
Data models for course catalog information.

Provides Python classes for representing course data with validation.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Union, Any
from datetime import datetime
import re


@dataclass
class Course:
    """
    Unified course data model conforming to the JSON schema.

    This class represents a single course from any university catalog,
    normalized to a consistent structure.
    """
    university: str
    course_id: str
    title: str
    description: str
    credits: Union[int, float, str]
    level: str
    department: str

    prerequisites: Optional[Dict[str, Any]] = None
    prerequisites_text: Optional[str] = None
    prerequisites_parsed: bool = False
    corequisites: Optional[List[str]] = None
    restrictions: Optional[str] = None
    offerings: Optional[List[str]] = None
    catalog_url: Optional[str] = None
    last_updated: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self):
        """Validate and normalize fields after initialization."""
        self.course_id = self._normalize_course_id(self.course_id)

        valid_levels = ["Undergraduate", "Graduate", "Professional", "Unknown"]
        if self.level not in valid_levels:
            self.level = "Unknown"

        if self.last_updated is None:
            self.last_updated = datetime.utcnow().isoformat() + "Z"

    @staticmethod
    def _normalize_course_id(course_id: str) -> str:
        """
        Normalize course ID to a consistent format.

        Examples:
            "CSE2100" -> "CSE 2100"
            "CS  101" -> "CS 101"
            "MATH-2410Q" -> "MATH 2410Q"
        """
        course_id = re.sub(r'[-\s]+', ' ', course_id.strip())
        course_id = re.sub(r'([A-Z]+)(\d)', r'\1 \2', course_id)
        course_id = re.sub(r'\s+', ' ', course_id)
        return course_id.upper()

    @staticmethod
    def infer_level(course_id: str, department: str = "") -> str:
        """
        Infer course level from course ID.

        Common patterns:
            - 1000-2999: Undergraduate lower division
            - 3000-4999: Undergraduate upper division
            - 5000-9999: Graduate
        """
        match = re.search(r'\d+', course_id)
        if match:
            number = int(match.group())
            if number < 5000:
                return "Undergraduate"
            else:
                return "Graduate"
        return "Unknown"

    def to_dict(self) -> Dict[str, Any]:
        """Convert course to dictionary, excluding None values."""
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}

    def validate(self) -> tuple[bool, List[str]]:
        """
        Validate course data against schema requirements.

        Returns:
            (is_valid, error_messages)
        """
        errors = []

        required = ['university', 'course_id', 'title', 'description',
                   'credits', 'level', 'department']
        for field_name in required:
            value = getattr(self, field_name)
            if not value or (isinstance(value, str) and not value.strip()):
                errors.append(f"Missing required field: {field_name}")

        if not re.match(r'^[A-Z]{2,6}\s*\d{3,4}[A-Z]?$', self.course_id):
            errors.append(f"Invalid course_id format: {self.course_id}")

        if isinstance(self.credits, str):
            if not re.match(r'^\d+(-\d+)?$', str(self.credits)):
                errors.append(f"Invalid credits format: {self.credits}")
        elif not isinstance(self.credits, (int, float)):
            errors.append(f"Credits must be number or string: {self.credits}")

        return (len(errors) == 0, errors)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"Course({self.university} {self.course_id}: {self.title})"


@dataclass
class CatalogMetadata:
    """
    Metadata about a scraped catalog.

    Tracks information about the scraping run for quality assurance.
    """
    university: str
    scrape_date: str
    total_courses: int
    successful_parses: int
    failed_parses: int
    catalog_url: str
    scraper_version: str

    @property
    def success_rate(self) -> float:
        """Calculate percentage of successfully parsed courses."""
        total = self.successful_parses + self.failed_parses
        if total == 0:
            return 0.0
        return (self.successful_parses / total) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['success_rate'] = self.success_rate
        return data
