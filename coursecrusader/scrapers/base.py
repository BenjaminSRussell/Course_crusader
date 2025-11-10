import scrapy
from abc import ABC, abstractmethod
from typing import Iterator, Optional, Dict, Any
from datetime import datetime

from ..models import Course, CatalogMetadata
from ..parsers import PrerequisiteParser, clean_text, extract_credits


class BaseCourseScraper(scrapy.Spider, ABC):
    name: str = "base_scraper"
    university: str = "Unknown"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prereq_parser = PrerequisiteParser()
        self.stats = {
            'courses_scraped': 0,
            'courses_parsed': 0,
            'parse_failures': 0,
            'start_time': datetime.utcnow().isoformat(),
        }

    @abstractmethod
    def parse(self, response):
        pass

    def create_course(self, **kwargs) -> Course:
        if 'university' not in kwargs:
            kwargs['university'] = self.university
        if 'last_updated' not in kwargs:
            kwargs['last_updated'] = datetime.utcnow().isoformat() + "Z"
        return Course(**kwargs)

    def parse_prerequisites(self, prereq_text: str) -> Dict[str, Any]:
        if not prereq_text:
            return {'prerequisites': None, 'prerequisites_text': None, 'prerequisites_parsed': True}
        prereq_text = clean_text(prereq_text)
        structured, success = self.prereq_parser.parse(prereq_text)
        return {'prerequisites': structured, 'prerequisites_text': prereq_text, 'prerequisites_parsed': success}

    def extract_course_id(self, text: str) -> Optional[str]:
        import re
        pattern = r'\b([A-Z]{2,6})[\s\-]*(\d{3,4}[A-Z]?)\b'
        match = re.search(pattern, text)
        if match:
            return f"{match.group(1)} {match.group(2)}"
        return None

    def clean_description(self, description: str) -> str:
        return clean_text(description)

    def normalize_credits(self, credit_text: str) -> Any:
        credits = extract_credits(credit_text)
        return credits if credits is not None else "Unknown"

    def infer_level(self, course_id: str) -> str:
        return Course.infer_level(course_id)

    def log_parse_success(self, course: Course):
        self.stats['courses_parsed'] += 1
        self.logger.debug(f"Parsed: {course.course_id} - {course.title}")

    def log_parse_failure(self, url: str, reason: str):
        self.stats['parse_failures'] += 1
        self.logger.warning(f"Parse failure at {url}: {reason}")

    def closed(self, reason):
        self.stats['end_time'] = datetime.utcnow().isoformat()
        self.logger.info(f"Scraping Statistics for {self.university}: Courses Scraped: {self.stats['courses_scraped']}, Successfully Parsed: {self.stats['courses_parsed']}, Parse Failures: {self.stats['parse_failures']}, Success Rate: {self._calculate_success_rate():.2f}%, Duration: {self._calculate_duration()}")

    def _calculate_success_rate(self) -> float:
        total = self.stats['courses_parsed'] + self.stats['parse_failures']
        if total == 0:
            return 0.0
        return (self.stats['courses_parsed'] / total) * 100

    def _calculate_duration(self) -> str:
        try:
            from datetime import datetime
            start = datetime.fromisoformat(self.stats['start_time'])
            end = datetime.fromisoformat(self.stats['end_time'])
            duration = end - start
            return str(duration)
        except:
            return "Unknown"

    def validate_course(self, course: Course) -> tuple[bool, list]:
        return course.validate()
