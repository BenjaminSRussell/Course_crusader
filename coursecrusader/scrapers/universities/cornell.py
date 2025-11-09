"""
Cornell University course catalog scraper.
"""

import scrapy
import re
from ..base import BaseCourseScraper
from ..registry import register_scraper
from ...parsers import clean_text, extract_credits


@register_scraper
class CornellScraper(BaseCourseScraper):
    """Scraper for Cornell course catalog."""

    name = "cornell"
    university = "Cornell University"

    start_urls = ['https://classes.cornell.edu/browse/roster/FA23']

    custom_settings = {
        'FEEDS': {
            'cornell_courses.jsonl': {
                'format': 'jsonlines',
                'encoding': 'utf-8',
                'overwrite': True,
            },
        },
    }

    def parse(self, response):
        """Parse Cornell roster."""
        self.logger.info(f"Parsing Cornell courses: {response.url}")

        dept_links = response.css('a.subject-link::attr(href)').getall()

        for link in dept_links:
            yield response.follow(link, callback=self.parse_department)

    def parse_department(self, response):
        """Parse department courses."""
        dept_name = response.css('h1::text').get() or "Unknown"

        course_blocks = response.css('.course-block')

        for block in course_blocks:
            course = self._parse_course_block(block, dept_name, response.url)
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
                credits=extract_credits(block.css('.credits::text').get()) or 3,
                level=self.infer_level(course_id),
                department=dept_name,
                catalog_url=page_url
            )

        return None
