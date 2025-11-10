"""
Yale University course catalog scraper.

Yale uses yet another catalog format - demonstrates flexibility of framework.
"""

import scrapy
import re
from typing import Iterator

from ..base import BaseCourseScraper
from ..registry import register_scraper
from ...parsers import clean_text, extract_credits


@register_scraper
class YaleScraper(BaseCourseScraper):
    """
    Scraper for Yale course catalog.

    Yale's catalog provides another example of catalog format variation.
    """

    name = "yale"
    university = "Yale University"

    start_urls = [
        'https://catalog.yale.edu/courses/'
    ]

    custom_settings = {
        'FEEDS': {
            'yale_courses.jsonl': {
                'format': 'jsonlines',
                'encoding': 'utf-8',
                'overwrite': True,
            },
        },
    }

    def parse(self, response):
        """Parse the main course listing page."""
        self.logger.info(f"Parsing Yale courses page: {response.url}")

        # Find department/subject links
        dept_links = response.css('a[href*="/courses/"]::attr(href)').getall()

        dept_links = [
            link for link in dept_links
            if re.search(r'/courses/[a-z]+/$', link.lower())
        ]

        self.logger.info(f"Found {len(dept_links)} departments")

        for link in dept_links:
            yield response.follow(link, callback=self.parse_department)

    def parse_department(self, response):
        """Parse department page with courses."""
        self.logger.info(f"Parsing Yale department: {response.url}")

        dept_name = self._extract_department_name(response)

        course_blocks = response.css('div.course-block')

        if not course_blocks:
            course_blocks = response.css('div.courseblock, div[class*="course"]')

        self.logger.info(f"Found {len(course_blocks)} courses in {dept_name}")

        for block in course_blocks:
            try:
                course = self._parse_course_block(block, dept_name, response.url)
                if course:
                    self.log_parse_success(course)
                    yield course
                    self.stats['courses_scraped'] += 1
            except Exception as e:
                self.log_parse_failure(response.url, str(e))

    def _extract_department_name(self, response) -> str:
        """Extract department name."""
        title = response.css('h1::text, h2::text').get()
        if title:
            return title.strip()

        match = re.search(r'/courses/([^/]+)/', response.url)
        if match:
            return match.group(1).upper()

        return "Unknown"

    def _parse_course_block(self, block, dept_name: str, page_url: str):
        """
        Parse Yale course block.

        Yale format typically: "CPSC 201. Introduction to Computer Science"
        """
        # Extract title line with course code
        title_elem = block.css('h3::text, .course-title::text').get()

        if not title_elem:
            title_elem = block.css('::text').get()

        if not title_elem:
            return None

        # Parse format: "DEPT NNN. Title"
        pattern = r'^([A-Z]{2,6})\s+(\d{3,4}[A-Z]?)\.\s+(.+?)(?:\s*\.\s*)?$'
        match = re.match(pattern, title_elem.strip())

        if not match:
            return None

        dept_code = match.group(1)
        number = match.group(2)
        title = match.group(3).strip()

        course_id = f"{dept_code} {number}"

        desc_elem = block.css('p.description::text, div.description::text').get()
        if not desc_elem:
            desc_parts = block.css('p::text').getall()
            desc_elem = ' '.join(desc_parts)

        description = clean_text(desc_elem) if desc_elem else ""

        credits = extract_credits(block.css('::text').getall().__str__())

        prereq_data = self._extract_prerequisites(block, description)

        level = self.infer_level(course_id)

        course = self.create_course(
            course_id=course_id,
            title=title,
            description=description,
            credits=credits if credits else "Unknown",
            level=level,
            department=dept_name,
            catalog_url=page_url,
            **prereq_data
        )

        return course

    def _extract_prerequisites(self, block, description: str) -> dict:
        """Extract prerequisites."""
        prereq_elem = block.css('.prerequisites::text, .prereq::text').get()

        if prereq_elem:
            prereq_text = clean_text(prereq_elem)
            return self.parse_prerequisites(prereq_text)

        prereq_match = re.search(
            r'(?:prerequisite|prereq)[s]?\s*:\s*([^.]+)',
            description,
            re.IGNORECASE
        )

        if prereq_match:
            prereq_text = prereq_match.group(1).strip()
            return self.parse_prerequisites(prereq_text)

        return {
            'prerequisites': None,
            'prerequisites_text': None,
            'prerequisites_parsed': True,
        }
