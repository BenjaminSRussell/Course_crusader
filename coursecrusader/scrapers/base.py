"""
Base scraper class for course catalogs.

All university-specific scrapers inherit from this class.
"""

import scrapy
from abc import ABC, abstractmethod
from typing import Iterator, Optional, Dict, Any
from datetime import datetime

from ..models import Course, CatalogMetadata
from ..parsers import PrerequisiteParser, clean_text, extract_credits


class BaseCourseScraper(scrapy.Spider, ABC):
    """
    Abstract base class for university course catalog scrapers.

    Each university scraper inherits from this and implements:
    - name: Unique identifier for the scraper
    - university: Full university name
    - start_urls: List of URLs to begin crawling
    - parse(): Main parsing logic
    """

    # Must be overridden by subclasses
    name: str = "base_scraper"
    university: str = "Unknown"

    def __init__(self, *args, **kwargs):
        """Initialize the scraper."""
        super().__init__(*args, **kwargs)

        self.prereq_parser = PrerequisiteParser()

        # Statistics tracking
        self.stats = {
            'courses_scraped': 0,
            'courses_parsed': 0,
            'parse_failures': 0,
            'start_time': datetime.utcnow().isoformat(),
        }

    @abstractmethod
    def parse(self, response):
        """
        Main parsing method - must be implemented by subclasses.

        Should yield Course objects or Requests for more pages.
        """
        pass

    def create_course(self, **kwargs) -> Course:
        """
        Create a Course object with university and timestamp automatically set.

        Args:
            **kwargs: Course fields (course_id, title, description, etc.)

        Returns:
            Course object
        """
        # Ensure university is set
        if 'university' not in kwargs:
            kwargs['university'] = self.university

        # Set timestamp
        if 'last_updated' not in kwargs:
            kwargs['last_updated'] = datetime.utcnow().isoformat() + "Z"

        return Course(**kwargs)

    def parse_prerequisites(self, prereq_text: str) -> Dict[str, Any]:
        """
        Parse prerequisite text into structured format.

        Args:
            prereq_text: Raw prerequisite string

        Returns:
            Dict with 'prerequisites', 'prerequisites_text', and 'prerequisites_parsed'
        """
        if not prereq_text:
            return {
                'prerequisites': None,
                'prerequisites_text': None,
                'prerequisites_parsed': True,
            }

        # Clean the text
        prereq_text = clean_text(prereq_text)

        # Parse
        structured, success = self.prereq_parser.parse(prereq_text)

        return {
            'prerequisites': structured,
            'prerequisites_text': prereq_text,
            'prerequisites_parsed': success,
        }

    def extract_course_id(self, text: str) -> Optional[str]:
        """
        Extract course ID from text.

        Override this in subclasses if the university has a unique format.
        """
        import re

        # Standard pattern: 2-6 letters, space/hyphen, 3-4 digits, optional letter
        pattern = r'\b([A-Z]{2,6})[\s\-]*(\d{3,4}[A-Z]?)\b'
        match = re.search(pattern, text)

        if match:
            dept = match.group(1)
            number = match.group(2)
            return f"{dept} {number}"

        return None

    def clean_description(self, description: str) -> str:
        """Clean and normalize course description text."""
        return clean_text(description)

    def normalize_credits(self, credit_text: str) -> Any:
        """
        Extract and normalize credit hours.

        Returns int, float, or string depending on format.
        """
        credits = extract_credits(credit_text)
        return credits if credits is not None else "Unknown"

    def infer_level(self, course_id: str) -> str:
        """
        Infer course level from course ID.

        Can be overridden by subclasses with university-specific logic.
        """
        return Course.infer_level(course_id)

    def log_parse_success(self, course: Course):
        """Log successful course parse."""
        self.stats['courses_parsed'] += 1
        self.logger.debug(f"Parsed: {course.course_id} - {course.title}")

    def log_parse_failure(self, url: str, reason: str):
        """Log failed course parse."""
        self.stats['parse_failures'] += 1
        self.logger.warning(f"Parse failure at {url}: {reason}")

    def closed(self, reason):
        """
        Called when spider closes.

        Log final statistics.
        """
        self.stats['end_time'] = datetime.utcnow().isoformat()

        self.logger.info(f"""
        Scraping Statistics for {self.university}:
        - Courses Scraped: {self.stats['courses_scraped']}
        - Successfully Parsed: {self.stats['courses_parsed']}
        - Parse Failures: {self.stats['parse_failures']}
        - Success Rate: {self._calculate_success_rate():.2f}%
        - Duration: {self._calculate_duration()}
        """)

    def _calculate_success_rate(self) -> float:
        """Calculate parsing success rate."""
        total = self.stats['courses_parsed'] + self.stats['parse_failures']
        if total == 0:
            return 0.0
        return (self.stats['courses_parsed'] / total) * 100

    def _calculate_duration(self) -> str:
        """Calculate scraping duration."""
        try:
            from datetime import datetime
            start = datetime.fromisoformat(self.stats['start_time'])
            end = datetime.fromisoformat(self.stats['end_time'])
            duration = end - start
            return str(duration)
        except:
            return "Unknown"

    def validate_course(self, course: Course) -> tuple[bool, list]:
        """
        Validate a course object.

        Returns:
            (is_valid, errors)
        """
        return course.validate()
