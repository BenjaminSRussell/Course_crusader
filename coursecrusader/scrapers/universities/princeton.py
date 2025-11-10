"""
Princeton University course catalog scraper.
"""

import scrapy
import re
from ..base import BaseCourseScraper
from ..registry import register_scraper
from ...parsers import clean_text, extract_credits


@register_scraper
class PrincetonScraper(BaseCourseScraper):
    """Scraper for Princeton course catalog."""

    name = "princeton"
    university = "Princeton University"

    start_urls = ['https://registrar.princeton.edu/course-offerings']

    custom_settings = {
        'FEEDS': {
            'princeton_courses.jsonl': {
                'format': 'jsonlines',
                'encoding': 'utf-8',
                'overwrite': True,
            },
        },
    }

    def parse(self, response):
        """Parse Princeton courses."""
        self.logger.info(f"Parsing Princeton courses: {response.url}")

        course_blocks = response.css('.course')

        for block in course_blocks:
            course = self._parse_course_block(block, "Princeton", response.url)
            if course:
                yield course

    def _parse_course_block(self, block, dept_name, page_url):
        """Parse course."""
        title_elem = block.css('.course-title::text').get()

        if not title_elem:
            return None

        match = re.match(r'([A-Z]+)\s+(\d+)', title_elem)

        if match:
            course_id = f"{match.group(1)} {match.group(2)}"

            return self.create_course(
                course_id=course_id,
                title=title_elem,
                description=block.css('.description::text').get() or "",
                credits=3,
                level=self.infer_level(course_id),
                department=dept_name,
                catalog_url=page_url
            )

        return None
