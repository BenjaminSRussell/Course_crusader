"""
Harvard University course catalog scraper.

Harvard's course catalog system.
"""

import scrapy
import re
from ..base import BaseCourseScraper
from ..registry import register_scraper
from ...parsers import clean_text, extract_credits


@register_scraper
class HarvardScraper(BaseCourseScraper):
    """Scraper for Harvard course catalog."""

    name = "harvard"
    university = "Harvard University"
    start_urls = ['https://courses.my.harvard.edu/']



    def parse(self, response):
        """Parse Harvard courses page."""
        self.logger.info(f"Parsing Harvard courses: {response.url}")

        # Note: Harvard's actual catalog might require API access or JS rendering
        # This is a template that would need adjustment based on their actual structure

        course_blocks = response.css('.course-block')

        for block in course_blocks:
            course = self._parse_course_block(block, "Harvard", response.url)
            yield from self._process_course_block(course, response.url)

    def _parse_course_block(self, block, dept_name, page_url):
        """Parse course block."""
        # Harvard format varies - this is a template
        title_elem = block.css('.course-title::text').get()

        if not title_elem:
            return None

        # Basic parsing - would need customization
        match = re.match(r'([A-Z]+)\s+(\d+)', title_elem)

        if match:
            course_id = f"{match.group(1)} {match.group(2)}"
            title = title_elem.split(':', 1)[1].strip() if ':' in title_elem else title_elem

            return self.create_course(
                course_id=course_id,
                title=title,
                description=block.css('.description::text').get() or "",
                credits=3,
                level=self.infer_level(course_id),
                department=dept_name,
                catalog_url=page_url
            )

        return None
