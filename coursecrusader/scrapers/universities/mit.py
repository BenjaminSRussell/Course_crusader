"""
MIT (Massachusetts Institute of Technology) course catalog scraper.
"""

import scrapy
import re
from typing import Iterator

from ..base import BaseCourseScraper
from ..registry import register_scraper
from ...parsers import clean_text, extract_credits


@register_scraper
class MITScraper(BaseCourseScraper):
    """
    Scraper for MIT course catalog.

    MIT's catalog is organized by department with a different HTML structure.
    """

    name = "mit"
    university = "Massachusetts Institute of Technology"
    start_urls = [
        'http://catalog.mit.edu/subjects/'
    ]



    def parse(self, response):
        """
        Parse the main subjects page.

        MIT organizes courses by subject/department.
        """
        self.logger.info(f"Parsing MIT subjects page: {response.url}")

        # Find all subject/department links
        # MIT typically has links like /subjects/1/ for Course 1, etc.
        subject_links = response.css('a[href*="/subjects/"]::attr(href)').getall()

        # Filter to only numeric subject pages
        subject_links = [
            link for link in subject_links
            if re.search(r'/subjects/[\w-]+/$', link)
        ]

        self.logger.info(f"Found {len(subject_links)} subject areas")

        for link in subject_links:
            yield response.follow(link, callback=self.parse_subject)

    def parse_subject(self, response):
        """
        Parse a subject/department page.

        Each subject has multiple courses listed.
        """
        self.logger.info(f"Parsing MIT subject page: {response.url}")

        # Extract department/subject name
        dept_name = self._extract_department_name(response)

        # MIT uses different selectors - adapt based on actual structure
        # This is a template that would need to be adjusted to MIT's actual HTML
        course_blocks = response.css('div.course, div.subject-course')

        if not course_blocks:
            # Alternative: look for any structure with course numbers
            # MIT courses typically like "6.001" or "18.01"
            course_blocks = response.xpath('//div[contains(., ".") and matches(., "\\d+\\.\\d+")]')

        self.logger.info(f"Found {len(course_blocks)} courses in {dept_name}")

        for block in course_blocks:
            course = self._parse_course_block(block, dept_name, response.url)
            yield from self._process_course_block(course, response.url)

    def _extract_department_name(self, response) -> str:
        """Extract department name from subject page."""
        title = response.css('h1::text').get()
        if title:
            return title.strip()

        page_title = response.css('title::text').get()
        if page_title:
            # Remove "| MIT Catalog" or similar
            title = re.sub(r'\s*\|.*$', '', page_title)
            return title.strip()

        match = re.search(r'/subjects/([\w-]+)/', response.url)
        if match:
            return f"Course {match.group(1)}"

        return "Unknown"

    def _parse_course_block(self, block, dept_name: str, page_url: str):
        """
        Parse a single MIT course block.

        MIT course format: "6.001 Structure and Interpretation of Computer Programs"
        """
        text = ' '.join(block.css('::text').getall())
        text = clean_text(text)

        # Extract course number (MIT format like "6.001" or "18.01")
        course_match = re.search(r'(\d+\.[\dA-Z]+)', text)
        if not course_match:
            return None

        course_num = course_match.group(1)

        # MIT course IDs are just numbers, but we'll format as "Course N"
        course_id = course_num

        # Extract title - usually after the course number
        title_match = re.search(rf'{re.escape(course_num)}\s+(.+?)(?:\.|$)', text)
        if title_match:
            title = title_match.group(1).strip()
        else:
            title = "Unknown"

        # Extract description - typically in a separate element or paragraph
        desc_elem = block.css('p.description::text, .course-desc::text').get()
        description = clean_text(desc_elem) if desc_elem else text

        # Extract credits (units in MIT terminology)
        credits = extract_credits(text)
        if not credits:
            # MIT often uses format like "3-0-9" (lecture-lab-preparation hours)
            units_match = re.search(r'(\d+-\d+-\d+)', text)
            if units_match:
                # Convert to total units (first number is usually credit hours)
                units = units_match.group(1).split('-')
                credits = int(units[0])

        prereq_data = self._extract_prerequisites(text, description)

        # MIT courses are typically undergraduate or graduate based on number
        # 100-999 are undergrad, 1000+ are grad (varies by department)
        level = self._infer_mit_level(course_num)

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

    def _infer_mit_level(self, course_num: str) -> str:
        """Infer course level from MIT course number."""
        parts = course_num.split('.')

        if len(parts) > 1:
            num_str = parts[1]
        else:
            num_str = parts[0]

        num_str = ''.join(filter(str.isdigit, num_str))

        if not num_str:
            return "Unknown"

        try:
            num = int(num_str)
        except (ValueError, IndexError):
            return "Unknown"

        if num >= 500:
            return "Graduate"
        else:
            return "Undergraduate"

    def _extract_prerequisites(self, text: str, description: str) -> dict:
        """Extract prerequisites from course text."""
        prereq_match = re.search(
            r'(?:prerequisite|prereq)[s]?\s*[:\-]\s*([^.;]+)',
            text + ' ' + description,
            re.IGNORECASE
        )

        if prereq_match:
            prereq_text = clean_text(prereq_match.group(1))
            return self.parse_prerequisites(prereq_text)

        return {
            'prerequisites': None,
            'prerequisites_text': None,
            'prerequisites_parsed': True,
        }
