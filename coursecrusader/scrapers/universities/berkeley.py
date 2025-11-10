"""
UC Berkeley course catalog scraper.

Berkeley uses the UCB Course Catalog.
"""

import scrapy
import re
from typing import Iterator

from ..base import BaseCourseScraper
from ..registry import register_scraper
from ...parsers import clean_text, extract_credits


@register_scraper
class BerkeleyScraper(BaseCourseScraper):
    """
    Scraper for UC Berkeley course catalog.
    """

    name = "berkeley"
    university = "University of California, Berkeley"

    start_urls = [
        'https://guide.berkeley.edu/courses/'
    ]

    custom_settings = {
        'FEEDS': {
            'berkeley_courses.jsonl': {
                'format': 'jsonlines',
                'encoding': 'utf-8',
                'overwrite': True,
            },
        },
    }

    def parse(self, response):
        """Parse the main courses page."""
        self.logger.info(f"Parsing Berkeley courses: {response.url}")

        # Find department links
        dept_links = response.css('a[href*="/courses/"]::attr(href)').getall()

        # Filter for actual department pages
        dept_links = [l for l in dept_links if re.search(r'/courses/[a-z]+/$', l.lower())]

        self.logger.info(f"Found {len(dept_links)} departments")

        for link in dept_links:
            yield response.follow(link, callback=self.parse_department)

    def parse_department(self, response):
        """Parse department page."""
        dept_name = response.css('h1.page-title::text').get() or "Unknown"

        course_blocks = response.css('.courseblock')

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

    def _parse_course_block(self, block, dept_name: str, page_url: str):
        """Parse course block."""
        # Berkeley format: "COMPSCI 61A. Structure and Interpretation of Computer Programs. 4 Units."
        title_elem = block.css('.courseblocktitle::text').get()

        if not title_elem:
            return None

        # Parse title
        pattern = r'([A-Z]+)\s+(\d+[A-Z]?)\.\s+(.+?)(?:\.\s+(\d+)\s+Units?)?'
        match = re.match(pattern, title_elem)

        if not match:
            return None

        dept_code = match.group(1)
        number = match.group(2)
        title = match.group(3).strip()
        credits = match.group(4) if match.group(4) else 3

        course_id = f"{dept_code} {number}"

        # Description
        desc_elem = block.css('.courseblockdesc::text').get()
        description = clean_text(desc_elem) if desc_elem else ""

        # Prerequisites
        prereq_text = block.css('.prereq::text').get()
        prereq_data = self.parse_prerequisites(prereq_text) if prereq_text else {
            'prerequisites': None,
            'prerequisites_text': None,
            'prerequisites_parsed': True
        }

        level = self.infer_level(course_id)

        return self.create_course(
            course_id=course_id,
            title=title,
            description=description,
            credits=credits,
            level=level,
            department=dept_name,
            catalog_url=page_url,
            **prereq_data
        )
