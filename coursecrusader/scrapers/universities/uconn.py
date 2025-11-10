import scrapy
import re
from typing import Iterator

from ..base import BaseCourseScraper
from ..registry import register_scraper
from ...parsers import clean_text, extract_credits


@register_scraper
class UConnScraper(BaseCourseScraper):
    name = "uconn"
    university = "University of Connecticut"
    start_urls = ['https://catalog.uconn.edu/undergraduate/courses/']

    custom_settings = {
        'FEEDS': {
            'uconn_courses.jsonl': {
                'format': 'jsonlines',
                'encoding': 'utf-8',
                'overwrite': True,
            },
        },
        'DOWNLOAD_DELAY': 1.5,
        'CONCURRENT_REQUESTS': 2,
    }

    def parse(self, response):
        self.logger.info(f"Parsing course listing page: {response.url}")
        dept_links = response.css('a::attr(href)').re(r'/undergraduate/courses/[a-z]+/')
        if not dept_links:
            dept_links = response.css('a::attr(href)').re(r'/graduate/courses/[a-z]+/')
        dept_links = list(set(dept_links))
        self.logger.info(f"Found {len(dept_links)} department links")
        for link in dept_links:
            yield response.follow(link, callback=self.parse_department)

    def parse_department(self, response):
        self.logger.info(f"Parsing department page: {response.url}")
        dept_name = self._extract_department_name(response)
        course_blocks = response.css('div.courseblock')
        if not course_blocks:
            course_blocks = response.css('div.course')
        self.logger.info(f"Found {len(course_blocks)} courses in {dept_name}")
        for block in course_blocks:
            try:
                course_link = block.css('a.bubblelink::attr(href)').get()
                if not course_link:
                    course_link = block.css('a.courseblockcode::attr(href)').get()
                if course_link:
                    yield response.follow(course_link, callback=self.parse_course_detail,
                                        meta={'dept_name': dept_name, 'block': block})
                else:
                    course = self._parse_course_block(block, dept_name, response.url)
                    if course:
                        self.log_parse_success(course)
                        yield course
                        self.stats['courses_scraped'] += 1
            except Exception as e:
                self.log_parse_failure(response.url, str(e))

    def parse_course_detail(self, response):
        dept_name = response.meta.get('dept_name', 'Unknown')
        course_block = response.css('div.courseblock').get() or response.css('div.course').get()
        if course_block:
            course = self._parse_course_block(response.css('div.courseblock, div.course'),
                                             dept_name, response.url)
        else:
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
        title = response.css('h1::text').get()
        if title:
            title = re.sub(r'\s*\([A-Z]+\)\s*', '', title)
            return title.strip()
        breadcrumb = response.css('.breadcrumb li:last-child::text').get()
        if breadcrumb:
            return breadcrumb.strip()
        match = re.search(r'/courses/([a-z]+)/', response.url)
        if match:
            return match.group(1).upper()
        return "Unknown"

    def _parse_course_block(self, block, dept_name: str, page_url: str):
        code_elem = block.css('.detail-code::text').get()
        title_elem = block.css('.detail-title::text').get()
        credits_elem = block.css('.detail-hours_html::text').get()
        if not code_elem or not title_elem:
            self.logger.warning(f"No course code or title found at {page_url}")
            return None
        course_id = clean_text(code_elem).rstrip('.')
        course_title = clean_text(title_elem).rstrip('.')
        credits = extract_credits(credits_elem) if credits_elem else "Unknown"
        desc_elem = block.css('.courseblockextra::text').get()
        description = clean_text(desc_elem) if desc_elem else ""
        prereq_data = self._extract_prerequisites(block, description)
        level = self.infer_level(course_id)
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
        pattern = r'^([A-Z]{2,6})\s+(\d{3,4}[A-Z]?)\.\s+(.+?)(?:\.\s+(.+))?$'
        match = re.match(pattern, title_text.strip())
        if match:
            dept = match.group(1)
            number = match.group(2)
            title = match.group(3).strip()
            last_part = match.group(4) if match.group(4) else ""
            credits = extract_credits(last_part) if last_part else None
            course_id = f"{dept} {number}"
            return course_id, title, credits
        pattern2 = r'^([A-Z]{2,6})\s+(\d{3,4}[A-Z]?)\.\s+(.+)$'
        match2 = re.match(pattern2, title_text.strip())
        if match2:
            dept = match2.group(1)
            number = match2.group(2)
            title = match2.group(3).strip().rstrip('.')
            course_id = f"{dept} {number}"
            credits = extract_credits(title)
            return course_id, title, credits
        return None, None, None

    def _extract_prerequisites(self, block, description: str) -> dict:
        prereq_elem = block.css('.detail-prereqs::text, .detail-reqs::text').get()
        prereq_text = None
        if prereq_elem:
            prereq_text = clean_text(prereq_elem)
        else:
            prereq_match = re.search(r'(?:prerequisite|prereq)[s]?\s*:\s*([^.]+)',
                                    description, re.IGNORECASE)
            if prereq_match:
                prereq_text = prereq_match.group(1).strip()
        if prereq_text:
            return self.parse_prerequisites(prereq_text)
        else:
            return {'prerequisites': None, 'prerequisites_text': None, 'prerequisites_parsed': True}
