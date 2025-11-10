"""
Stanford University course catalog scraper.

Stanford's Explore Courses system.
"""

import scrapy
import re
from typing import Iterator

from ..base import BaseCourseScraper
from ..registry import register_scraper
from ...parsers import clean_text, extract_credits


@register_scraper
class StanfordScraper(BaseCourseScraper):
    """
    Scraper for Stanford University course catalog.
    """

    name = "stanford"
    university = "Stanford University"
    start_urls = [
        'https://explorecourses.stanford.edu/'
    ]



    def parse(self, response):
        """Parse the main explore courses page."""
        self.logger.info(f"Parsing Stanford courses page: {response.url}")

        # Find department/school links
        dept_links = response.css('a[href*="/search"]::attr(href)').getall()

        self.logger.info(f"Found {len(dept_links)} department links")

        for link in dept_links[:5]:
            yield response.follow(link, callback=self.parse_department)

    def parse_department(self, response):
        """Parse department course listing."""
        self.logger.info(f"Parsing Stanford department: {response.url}")

        dept_name = response.css('h1::text').get() or "Unknown"

        course_blocks = response.css('.searchResult')

        self.logger.info(f"Found {len(course_blocks)} courses in {dept_name}")

        for block in course_blocks:
            course = self._parse_course_block(block, dept_name, response.url)
            yield from self._process_course_block(course, response.url)

    def _parse_course_block(self, block, dept_name: str, page_url: str):
        """Parse individual course block."""
        # Stanford format: "CS 101: Introduction to Computing"
        title_elem = block.css('.courseTitle::text').get()

        if not title_elem:
            return None

        match = re.match(r'([A-Z]+)\s+(\d+[A-Z]?):?\s+(.+)', title_elem)

        if not match:
            return None

        dept_code = match.group(1)
        number = match.group(2)
        title = match.group(3).strip()

        course_id = f"{dept_code} {number}"

        desc_elem = block.css('.courseDescription::text').get()
        description = clean_text(desc_elem) if desc_elem else ""

        # Extract credits (units in Stanford terminology)
        credits_elem = block.css('.units::text').get()
        credits = extract_credits(credits_elem) if credits_elem else 3

        prereq_text = block.css('.prerequisites::text').get()
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
