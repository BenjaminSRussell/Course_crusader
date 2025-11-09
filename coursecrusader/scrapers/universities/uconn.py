"""
UConn (University of Connecticut) course catalog scraper.

Scrapes courses from UConn's online catalog.
"""

import scrapy
import re
from typing import Iterator

from ..base import BaseCourseScraper
from ..registry import register_scraper
from ...parsers import clean_text, extract_credits


@register_scraper
class UConnScraper(BaseCourseScraper):
    """
    Scraper for University of Connecticut course catalog.

    UConn uses a CourseLeaf-based catalog system with courses organized
    by department. Each course has a dedicated page with structured information.
    """

    name = "uconn"
    university = "University of Connecticut"

    # Start with the A-Z course listing
    start_urls = [
        'https://catalog.uconn.edu/course-descriptions/'
    ]

    custom_settings = {
        'FEEDS': {
            'uconn_courses.jsonl': {
                'format': 'jsonlines',
                'encoding': 'utf-8',
                'overwrite': True,
            },
        },
    }

    def parse(self, response):
        """
        Parse the main course listing page.

        Finds links to all department/subject pages.
        """
        self.logger.info(f"Parsing course listing page: {response.url}")

        # Find all department links
        # CourseLeaf typically organizes courses by department with links
        dept_links = response.css('a.sitemaplink::attr(href)').getall()

        if not dept_links:
            # Try alternative selector
            dept_links = response.css('ul.programs a::attr(href)').getall()

        if not dept_links:
            # Try finding any links that look like course pages
            dept_links = response.css('a::attr(href)').re(r'/course-descriptions/[a-z]+/')

        self.logger.info(f"Found {len(dept_links)} department links")

        for link in dept_links:
            yield response.follow(link, callback=self.parse_department)

    def parse_department(self, response):
        """
        Parse a department page containing multiple courses.

        Each course is typically in a courseblock div.
        Tries to find individual course URLs if available.
        """
        self.logger.info(f"Parsing department page: {response.url}")

        # Extract department name from page
        dept_name = self._extract_department_name(response)

        # CourseLeaf uses courseblock divs for each course
        course_blocks = response.css('div.courseblock')

        if not course_blocks:
            # Try alternative structure
            course_blocks = response.css('div.course')

        self.logger.info(f"Found {len(course_blocks)} courses in {dept_name}")

        for block in course_blocks:
            try:
                # Check if this course has an individual detail page link
                course_link = block.css('a.bubblelink::attr(href)').get()
                if not course_link:
                    course_link = block.css('a.courseblockcode::attr(href)').get()

                if course_link:
                    # Follow to individual course page
                    yield response.follow(
                        course_link,
                        callback=self.parse_course_detail,
                        meta={'dept_name': dept_name, 'block': block}
                    )
                else:
                    # Parse course from this page (no individual URL)
                    course = self._parse_course_block(block, dept_name, response.url)
                    if course:
                        self.log_parse_success(course)
                        yield course
                        self.stats['courses_scraped'] += 1
            except Exception as e:
                self.log_parse_failure(response.url, str(e))

    def parse_course_detail(self, response):
        """
        Parse an individual course detail page.

        Args:
            response: Scrapy response from individual course page
        """
        dept_name = response.meta.get('dept_name', 'Unknown')

        # Try to find course block on detail page
        course_block = response.css('div.courseblock').get() or response.css('div.course').get()

        if course_block:
            # Parse from detail page structure
            course = self._parse_course_block(
                response.css('div.courseblock, div.course'),
                dept_name,
                response.url  # Individual course URL
            )
        else:
            # Fallback: use the block from meta if available
            block = response.meta.get('block')
            if block:
                course = self._parse_course_block(block, dept_name, response.url)
            else:
                self.logger.warning(f"Could not find course block on {response.url}")
                return

        if course:
            self.log_parse_success(course)
            yield course
            self.stats['courses_scraped'] += 1

    def _extract_department_name(self, response) -> str:
        """Extract department name from page."""
        # Try page title
        title = response.css('h1::text').get()
        if title:
            # Remove "Course Descriptions" or similar
            title = re.sub(r'\s*-?\s*Course Descriptions?', '', title, flags=re.IGNORECASE)
            return title.strip()

        # Try meta description or breadcrumb
        breadcrumb = response.css('.breadcrumb li:last-child::text').get()
        if breadcrumb:
            return breadcrumb.strip()

        # Fallback to URL
        match = re.search(r'/course-descriptions/([^/]+)/', response.url)
        if match:
            return match.group(1).upper()

        return "Unknown"

    def _parse_course_block(self, block, dept_name: str, page_url: str):
        """
        Parse a single course block into a Course object.

        Args:
            block: Scrapy selector for the course block
            dept_name: Department name
            page_url: URL of the page containing this course

        Returns:
            Course object or None if parsing fails
        """
        # Extract course title and code
        # Typical format: "CSE 1010. Introduction to Computing for Engineers."
        title_elem = block.css('.courseblocktitle::text').get()
        if not title_elem:
            title_elem = block.css('.course-title::text').get()

        if not title_elem:
            self.logger.warning(f"No title found in course block at {page_url}")
            return None

        # Parse title - format: "CODE NUMBER. Title. Credits."
        course_id, course_title, credits = self._parse_course_title(title_elem)

        if not course_id or not course_title:
            self.logger.warning(f"Failed to parse course title: {title_elem}")
            return None

        # Extract description
        desc_elem = block.css('.courseblockdesc::text').get()
        if not desc_elem:
            desc_elem = block.css('.course-description::text').get()

        description = clean_text(desc_elem) if desc_elem else ""

        # Extract additional description paragraphs if any
        extra_desc = block.css('.courseblockdesc p::text').getall()
        if extra_desc:
            description += " " + " ".join([clean_text(p) for p in extra_desc])

        # Look for prerequisites in description or separate field
        prereq_data = self._extract_prerequisites(block, description)

        # Infer level from course number
        level = self.infer_level(course_id)

        # Create course object
        course = self.create_course(
            course_id=course_id,
            title=course_title,
            description=description.strip(),
            credits=credits if credits else "Unknown",
            level=level,
            department=dept_name,
            catalog_url=page_url,
            **prereq_data
        )

        return course

    def _parse_course_title(self, title_text: str) -> tuple:
        """
        Parse course title string into components.

        Expected format: "CSE 1010. Introduction to Computing. 3 credits."

        Returns:
            (course_id, title, credits)
        """
        # Pattern: DEPT NUM. Title. Credits.
        # Example: "CSE 1010. Introduction to Computing for Engineers. 3 credits."
        pattern = r'^([A-Z]{2,6})\s+(\d{3,4}[A-Z]?)\.\s+(.+?)(?:\.\s+(.+))?$'
        match = re.match(pattern, title_text.strip())

        if match:
            dept = match.group(1)
            number = match.group(2)
            title = match.group(3).strip()

            # Extract credits from the last part
            last_part = match.group(4) if match.group(4) else ""
            credits = extract_credits(last_part) if last_part else None

            course_id = f"{dept} {number}"
            return course_id, title, credits

        # Alternative pattern without credits in title
        pattern2 = r'^([A-Z]{2,6})\s+(\d{3,4}[A-Z]?)\.\s+(.+)$'
        match2 = re.match(pattern2, title_text.strip())

        if match2:
            dept = match2.group(1)
            number = match2.group(2)
            title = match2.group(3).strip().rstrip('.')

            course_id = f"{dept} {number}"

            # Try to extract credits from title if present
            credits = extract_credits(title)

            return course_id, title, credits

        return None, None, None

    def _extract_prerequisites(self, block, description: str) -> dict:
        """
        Extract prerequisite information from course block or description.

        Returns dict with prerequisite fields.
        """
        # Look for a separate prerequisite field
        prereq_elem = block.css('.courseblockprereq::text').get()
        if not prereq_elem:
            prereq_elem = block.css('.prerequisites::text').get()

        prereq_text = None

        if prereq_elem:
            prereq_text = clean_text(prereq_elem)
        else:
            # Try to extract from description
            prereq_match = re.search(
                r'(?:prerequisite|prereq)[s]?\s*:\s*([^.]+)',
                description,
                re.IGNORECASE
            )
            if prereq_match:
                prereq_text = prereq_match.group(1).strip()

        if prereq_text:
            return self.parse_prerequisites(prereq_text)
        else:
            return {
                'prerequisites': None,
                'prerequisites_text': None,
                'prerequisites_parsed': True,
            }
